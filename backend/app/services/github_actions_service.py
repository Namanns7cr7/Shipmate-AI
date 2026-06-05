"""
GitHub Actions read helpers for the CI feedback loop.

Used by CIWatcher to poll the status of a Coder-opened PR and fetch the
failing job logs when CI breaks. All operations work under the existing
`repo` OAuth scope — reading Actions/Checks does NOT need the `workflow`
scope (only writing files under .github/workflows/ does).

Endpoints used:
  GET /repos/{o}/{r}/commits/{sha}/check-runs        — list checks for a SHA
  GET /repos/{o}/{r}/actions/jobs/{job_id}            — job + step metadata
  GET /repos/{o}/{r}/actions/jobs/{job_id}/logs       — 302 -> S3 plaintext
  GET /repos/{o}/{r}/check-runs/{id}/annotations      — structured fallback
  POST /repos/{o}/{r}/issues/{pr}/comments            — escalation comment
  GET /repos/{o}/{r}/git/ref/heads/{branch}           — current branch SHA

Logs are typically 50KB-2MB. We truncate to the last ~30k chars before
feeding back into Coder so we stay under Sonnet's context with headroom
(failures are at the tail of the log).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("shipmate.github_actions")

_BASE = "https://api.github.com"
_TIMEOUT = httpx.Timeout(30.0)
_LOG_TAIL_CHARS = 30_000


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


class CheckRunStatus:
    """Aggregate status of all check-runs for a SHA."""

    def __init__(self, runs: List[Dict[str, Any]]) -> None:
        self.runs = runs

    @property
    def all_completed(self) -> bool:
        return all(r.get("status") == "completed" for r in self.runs) and len(self.runs) > 0

    @property
    def any_failed(self) -> bool:
        bad = {"failure", "timed_out", "cancelled", "action_required"}
        return any(r.get("conclusion") in bad for r in self.runs)

    @property
    def failed_runs(self) -> List[Dict[str, Any]]:
        bad = {"failure", "timed_out", "cancelled", "action_required"}
        return [r for r in self.runs if r.get("conclusion") in bad]

    @property
    def all_passed(self) -> bool:
        return self.all_completed and not self.any_failed and len(self.runs) > 0

    @property
    def is_empty(self) -> bool:
        """No checks reported for this SHA — repo has no CI configured."""
        return len(self.runs) == 0


class GitHubActionsService:
    """Async helpers for inspecting GitHub Actions run state on a PR branch."""

    @staticmethod
    async def get_branch_head_sha(token: str, owner: str, repo: str, branch: str) -> str:
        """Current commit SHA at the tip of `branch`. Used to key check-run lookups."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/git/ref/heads/{branch}",
                headers=_headers(token),
            )
            resp.raise_for_status()
            return resp.json()["object"]["sha"]

    @staticmethod
    async def list_check_runs(
        token: str, owner: str, repo: str, ref: str,
    ) -> CheckRunStatus:
        """List all check-runs registered against a SHA."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/commits/{ref}/check-runs",
                headers=_headers(token),
                params={"per_page": 100},
            )
            resp.raise_for_status()
            return CheckRunStatus(resp.json().get("check_runs", []))

    @staticmethod
    async def fetch_job_logs(
        token: str, owner: str, repo: str, job_id: int,
    ) -> Optional[str]:
        """
        Fetch raw stdout/stderr for a failed Actions job. Returns the LAST
        ~30k characters (failures are at the tail). None if logs are gone
        (cancelled jobs sometimes 404 here — caller should fall back to
        annotations).

        Implementation: GitHub redirects /logs to a signed S3 URL. httpx
        follows redirects automatically when follow_redirects=True.
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0), follow_redirects=True) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
                headers=_headers(token),
            )
            if resp.status_code == 404:
                logger.info("Job %s logs unavailable (404) — likely cancelled", job_id)
                return None
            if resp.status_code >= 400:
                logger.warning(
                    "Job %s logs HTTP %s: %s",
                    job_id, resp.status_code, resp.text[:200],
                )
                return None
            text = resp.text or ""
            if len(text) > _LOG_TAIL_CHARS:
                head = f"... [log truncated; {len(text) - _LOG_TAIL_CHARS} chars omitted before this tail]\n\n"
                return head + text[-_LOG_TAIL_CHARS:]
            return text

    @staticmethod
    async def fetch_job_annotations(
        token: str, owner: str, repo: str, check_run_id: int,
    ) -> List[Dict[str, Any]]:
        """Structured failure annotations — fallback when raw logs are unavailable."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/repos/{owner}/{repo}/check-runs/{check_run_id}/annotations",
                headers=_headers(token),
            )
            if resp.status_code >= 400:
                return []
            return resp.json() or []

    @staticmethod
    async def post_pr_comment(
        token: str, owner: str, repo: str, pr_number: int, body: str,
    ) -> None:
        """Post a comment to a PR — used for escalation when watcher gives up."""
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=_headers(token),
                json={"body": body},
            )
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to post escalation comment on %s/%s#%s: %s",
                    owner, repo, pr_number, resp.text[:200],
                )

    @classmethod
    async def collect_failure_context(
        cls, token: str, owner: str, repo: str, status: CheckRunStatus,
    ) -> str:
        """
        Build a plaintext failure-context blob to feed back into Coder.
        Pulls logs (or annotations as fallback) for every failed check-run.
        Caller should wrap this string in a CoderBrief.target_files entry
        keyed e.g. "ci_failure.log".
        """
        chunks: List[str] = []
        for run in status.failed_runs:
            check_id = run.get("id")
            job_id = run.get("id")  # for Actions, check_run id == job id
            name = run.get("name", "?")
            conclusion = run.get("conclusion", "?")
            chunks.append(f"=== check-run: {name}  (conclusion: {conclusion}) ===")

            log = None
            if isinstance(job_id, int):
                log = await cls.fetch_job_logs(token, owner, repo, job_id)
            if log:
                chunks.append(log)
            else:
                # Fallback: structured annotations
                if isinstance(check_id, int):
                    anns = await cls.fetch_job_annotations(token, owner, repo, check_id)
                    if anns:
                        chunks.append("(no raw logs; using annotations)")
                        for a in anns[:20]:
                            chunks.append(
                                f"  [{a.get('annotation_level','?')}] "
                                f"{a.get('path','?')}:{a.get('start_line','?')} — "
                                f"{a.get('message','')[:300]}"
                            )
                    else:
                        chunks.append("(no logs and no annotations available)")
                else:
                    chunks.append("(no logs available)")
            chunks.append("")  # blank line between checks

        return "\n".join(chunks) if chunks else "(no failure context available)"
