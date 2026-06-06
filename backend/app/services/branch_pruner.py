"""
Branch graveyard pruner.

Lists `shipmate/*` refs and decides which to delete based on PR state:

  delete IF
    (a) linked PR is MERGED                        — the work is in main
    (b) linked PR is CLOSED unmerged AND > 7 days  — grace window for revival
    (c) NO PR was ever opened AND > 24h old        — orphaned attempt

  keep IF
    - linked PR is OPEN
    - branch is the head of any open PR (re-checked via /pulls?head=...)
    - branch is younger than 24h (still possibly being worked on)
    - branch is under branch protection

Standalone — does NOT depend on Guardian or any persistence layer. Safe
to call ad-hoc from /api/branches/prune. Returns a per-branch decision
report so the caller can render an "X branches pruned, Y kept" summary.

Run with `dry_run=True` (default) to PREVIEW deletions before committing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

import httpx

logger = logging.getLogger("shipmate.branch_pruner")

_BASE = "https://api.github.com"
_TIMEOUT = httpx.Timeout(20.0)
_BRANCH_PREFIX = "shipmate/"

# Grace windows
_CLOSED_GRACE_DAYS = 7
_NO_PR_GRACE_HOURS = 24


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@dataclass
class BranchDecision:
    name: str
    action: Literal["delete", "keep"]
    reason: str
    pr_number: Optional[int] = None
    pr_state: Optional[str] = None
    pr_url: Optional[str] = None


@dataclass
class PruneReport:
    owner: str
    repo: str
    dry_run: bool
    decisions: List[BranchDecision] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    kept: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "repo": self.repo,
            "dry_run": self.dry_run,
            "decisions": [
                {
                    "name": d.name,
                    "action": d.action,
                    "reason": d.reason,
                    "pr_number": d.pr_number,
                    "pr_state": d.pr_state,
                    "pr_url": d.pr_url,
                }
                for d in self.decisions
            ],
            "deleted_count": len(self.deleted),
            "kept_count": len(self.kept),
            "errors": self.errors,
        }


async def _list_shipmate_branches(
    token: str, owner: str, repo: str,
) -> List[Dict[str, Any]]:
    """Return refs starting with `shipmate/`, paginated."""
    branches: List[Dict[str, Any]] = []
    page = 1
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        while True:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/branches",
                headers=_headers(token),
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            chunk = resp.json()
            if not chunk:
                break
            branches.extend(b for b in chunk if b.get("name", "").startswith(_BRANCH_PREFIX))
            if len(chunk) < 100:
                break
            page += 1
    return branches


async def _find_pr_for_head(
    token: str, owner: str, repo: str, branch: str,
) -> Optional[Dict[str, Any]]:
    """Return the most recent PR (any state) whose head is `owner:branch`."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # state=all picks up merged PRs (which are "closed" in API terms)
        resp = await client.get(
            f"{_BASE}/repos/{owner}/{repo}/pulls",
            headers=_headers(token),
            params={"head": f"{owner}:{branch}", "state": "all", "per_page": 5},
        )
        if resp.status_code >= 400:
            logger.warning("PR lookup for %s failed: %s", branch, resp.text[:200])
            return None
        prs = resp.json()
        if not prs:
            return None
        # Most recently updated first
        prs.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return prs[0]


def _branch_age_hours(commit_iso: Optional[str]) -> Optional[float]:
    if not commit_iso:
        return None
    try:
        # GitHub returns ISO-8601 in 'Z' suffix
        dt = datetime.fromisoformat(commit_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


async def _branch_commit_date(
    token: str, owner: str, repo: str, sha: str,
) -> Optional[str]:
    """Get the commit's authored date so we can age-out orphan branches."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{_BASE}/repos/{owner}/{repo}/commits/{sha}",
            headers=_headers(token),
        )
        if resp.status_code >= 400:
            return None
        c = resp.json().get("commit", {}).get("committer", {})
        return c.get("date")


def _decide(
    branch: Dict[str, Any], pr: Optional[Dict[str, Any]], age_hours: Optional[float],
) -> BranchDecision:
    name = branch["name"]
    is_protected = branch.get("protected", False)
    if is_protected:
        return BranchDecision(name=name, action="keep", reason="branch is protected")

    if pr is None:
        # No PR ever opened — orphan attempt. Wait at least the grace window.
        if age_hours is None or age_hours < _NO_PR_GRACE_HOURS:
            return BranchDecision(
                name=name, action="keep",
                reason=f"no PR yet, branch age < {_NO_PR_GRACE_HOURS}h grace",
            )
        return BranchDecision(
            name=name, action="delete",
            reason=f"no PR opened in {_NO_PR_GRACE_HOURS}h grace window",
        )

    pr_number = pr.get("number")
    pr_url = pr.get("html_url")
    state = pr.get("state")  # 'open' or 'closed'
    merged = pr.get("merged_at") is not None

    if state == "open":
        return BranchDecision(
            name=name, action="keep", reason="linked PR is open",
            pr_number=pr_number, pr_state="open", pr_url=pr_url,
        )

    if merged:
        return BranchDecision(
            name=name, action="delete", reason="linked PR was merged",
            pr_number=pr_number, pr_state="merged", pr_url=pr_url,
        )

    # Closed unmerged → grace window
    closed_at = pr.get("closed_at")
    if closed_at:
        try:
            dt = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - dt).total_seconds() / 86400
            if days_since >= _CLOSED_GRACE_DAYS:
                return BranchDecision(
                    name=name, action="delete",
                    reason=f"PR closed unmerged > {_CLOSED_GRACE_DAYS}d ago",
                    pr_number=pr_number, pr_state="closed_unmerged", pr_url=pr_url,
                )
            return BranchDecision(
                name=name, action="keep",
                reason=f"PR closed unmerged < {_CLOSED_GRACE_DAYS}d (grace window)",
                pr_number=pr_number, pr_state="closed_unmerged", pr_url=pr_url,
            )
        except ValueError:
            pass

    return BranchDecision(
        name=name, action="keep", reason="closed-unmerged but no closed_at — being safe",
        pr_number=pr_number, pr_state="closed_unmerged", pr_url=pr_url,
    )


async def _delete_branch(
    token: str, owner: str, repo: str, branch: str,
) -> Optional[str]:
    """Returns None on success, error string on failure."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(
            f"{_BASE}/repos/{owner}/{repo}/git/refs/heads/{branch}",
            headers=_headers(token),
        )
        if resp.status_code in (204, 200):
            return None
        return f"{branch}: HTTP {resp.status_code} {resp.text[:200]}"


async def prune_shipmate_branches(
    token: str, owner: str, repo: str, dry_run: bool = True,
) -> PruneReport:
    """
    Inspect every `shipmate/*` branch and prune the ones whose linked PRs
    are merged or expired. Returns a full decision log.
    """
    report = PruneReport(owner=owner, repo=repo, dry_run=dry_run)

    try:
        branches = await _list_shipmate_branches(token, owner, repo)
    except Exception as e:
        report.errors.append(f"list branches failed: {e}")
        return report

    logger.info("BranchPruner: %s/%s — %d shipmate/* branches", owner, repo, len(branches))

    for b in branches:
        name = b["name"]
        try:
            pr = await _find_pr_for_head(token, owner, repo, name)
            commit_sha = b.get("commit", {}).get("sha")
            age_hours = None
            if pr is None and commit_sha:
                date = await _branch_commit_date(token, owner, repo, commit_sha)
                age_hours = _branch_age_hours(date)
            decision = _decide(b, pr, age_hours)
            report.decisions.append(decision)
            if decision.action == "delete":
                if dry_run:
                    report.deleted.append(name)  # would-be-deleted in dry run
                else:
                    err = await _delete_branch(token, owner, repo, name)
                    if err:
                        report.errors.append(err)
                        # Demote this decision so the caller sees what failed
                        decision.action = "keep"
                        decision.reason = f"delete failed: {err}"
                    else:
                        report.deleted.append(name)
            else:
                report.kept.append(name)
        except Exception as e:
            report.errors.append(f"{name}: {e}")

    logger.info(
        "BranchPruner: %s/%s — %s%d to delete, %d kept, %d errors",
        owner, repo, "(dry-run) " if dry_run else "", len(report.deleted),
        len(report.kept), len(report.errors),
    )
    return report
