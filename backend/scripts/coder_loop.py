"""
ShipMate Coder feedback loop — tight version.

Each round:
  1. Call /api/analyze against the current state of the repo branch
  2. Pick the TOP 1 of each kind (guardrail, milestone, blocker, test)
     so each round actuates ≤4 findings — not the whole audit.
  3. Run CoderAgent in PARALLEL across the 4 (cuts wall-clock ~4x).
  4. Lint each output; verdicts are local — no GitHub.
  5. APPLY the `good` patches to the local working tree (so the next
     round's analyze sees the change).
  6. Append a row to /tmp/coder_loop.jsonl per finding.
  7. Repeat until either:
       - --rounds N rounds are done, or
       - a full round produces 0 good patches (loop is dry).

This converts the audit harness into an actual feedback loop you can
review at the end — `git diff` shows what landed across N rounds.

Run:  python -m backend.scripts.coder_loop --rounds 3 --branch feat/bedrock-on-v2
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.agents.coder_agent import CoderAgent, CoderBrief, CoderOutput, CoderFile
from app.schemas.api_schemas import FindingPayload, RepoLensSummary
from app.services.coder_orchestrator import (
    _resolve_target_paths,
    _fetch_current_contents,
    _build_task,
    _deployment_hint,
    _lint_coder_output,
)
from app.services.github_api_service import GitHubAPIService

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("coder_loop")
logger.setLevel(logging.INFO)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Persistent dedup state — survives across `python coder_loop.py` invocations
# so we don't re-pick the same finding every time you re-run. Wipe with --reset.
_STATE_PATH = Path("/tmp/coder_loop_state.json")


def _load_state() -> Dict[str, Any]:
    if _STATE_PATH.exists():
        try:
            data = json.loads(_STATE_PATH.read_text())
            # Backfill new fields for older state files.
            data.setdefault("attempts", {})  # signature -> attempt count
            data.setdefault("parked", [])     # signatures permanently skipped
            return data
        except Exception:
            pass
    return {"seen_signatures": [], "baseline_passing": None,
            "attempts": {}, "parked": []}


_MAX_ATTEMPTS = 2  # findings that fail this many times go to `parked`


def _save_state(state: Dict[str, Any]) -> None:
    _STATE_PATH.write_text(json.dumps(state, indent=2))


# ── Pytest gate ──────────────────────────────────────────────────────────────


def _smoke_imports() -> Tuple[bool, str]:
    """Fast pre-pytest check: can we even import app.main? If not, the patch
    broke a top-level import and pytest will give a misleading 0p/68f result.
    Bounded by 10s. Returns (ok, error_text)."""
    import subprocess
    cwd = REPO_ROOT / "backend"
    try:
        proc = subprocess.run(
            ["./venv/bin/python", "-c", "import app.main"],
            cwd=str(cwd),
            capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "import smoke timeout"
    return proc.returncode == 0, (proc.stderr or proc.stdout or "")[-500:]


def _run_pytest(target: str = "backend/tests/") -> Tuple[int, int, str]:
    """Returns (passed, failed, raw_summary). Runs the test suite from
    REPO_ROOT/backend so app.* imports resolve. Uses -q + --tb=no for speed.
    Bounded by 90s to avoid hanging the loop on a slow test."""
    import subprocess
    cwd = REPO_ROOT / "backend"
    try:
        proc = subprocess.run(
            ["./venv/bin/python", "-m", "pytest", "tests/", "-q", "--tb=no",
             "--no-header", "-p", "no:cacheprovider"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return 0, 0, "pytest timeout"
    out = (proc.stdout or "") + (proc.stderr or "")
    # Pytest summary line looks like "5 failed, 67 passed in 0.27s"
    passed = failed = 0
    m = re.search(r"(\d+)\s+passed", out)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+)\s+failed", out)
    if m:
        failed = int(m.group(1))
    return passed, failed, out[-2000:]


def _baseline_pass_count(state: Dict[str, Any]) -> int:
    """Lazy-compute the baseline pass count. Stored across runs so the loop
    doesn't re-run tests every round if nothing has changed."""
    cached = state.get("baseline_passing")
    if cached is not None:
        return int(cached)
    passed, failed, _ = _run_pytest()
    state["baseline_passing"] = passed
    _save_state(state)
    return passed


# ── Verdict helpers ──────────────────────────────────────────────────────────

_TEST_THEATER_PATTERNS = [
    re.compile(r"status_code\s+in\s*[\(\[][^)\]]*4\d\d", re.MULTILINE),
    re.compile(r"^\s*assert\s+True\s*$", re.MULTILINE),
    re.compile(r"@pytest\.mark\.skip", re.MULTILINE),
]

_GITKEEP_THEATER = re.compile(
    r"(__pycache__|/build|/dist|/\.venv|/node_modules)/[^/]*\.gitkeep$"
)


def _looks_like_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        name.startswith("test_")
        or name.endswith((".test.tsx", ".test.ts", ".spec.ts", ".spec.tsx"))
        or "/tests/" in path
        or "/__tests__/" in path
    )


def _verdict_for(
    coder_out: CoderOutput,
    target_files: Dict[str, str],
    file_tree: List[str],
) -> Tuple[str, List[str]]:
    """Return (verdict, reasons). Reuses orchestrator's lint + extra checks."""
    if not coder_out.files:
        return "skipped", ["coder produced 0 files"]

    issues = list(_lint_coder_output(coder_out, target_files, file_tree))

    # Per-file extra: empty content (except __init__.py), gitkeep theater,
    # NEW test theater, mismatched first-party imports for tests.
    for cf in coder_out.files:
        if len(cf.new_content.strip()) < 20 and not cf.path.endswith("__init__.py"):
            issues.append(f"{cf.path}: file content is empty/trivial (<20 chars)")

        if _GITKEEP_THEATER.search(cf.path):
            issues.append(f"{cf.path}: .gitkeep theater pattern")

        if _looks_like_test(cf.path):
            original = target_files.get(cf.path, "")
            for pat in _TEST_THEATER_PATTERNS:
                if pat.search(cf.new_content) and not pat.search(original):
                    issues.append(
                        f"{cf.path}: NEW test theater `{pat.pattern[:50]}`"
                    )

    return ("bad" if issues else "good"), issues


# ── Pipeline pieces ──────────────────────────────────────────────────────────

async def _fetch_findings(
    base_url: str, owner: str, repo: str, branch: str, token: str,
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"{base_url}/api/analyze",
            json={"owner": owner, "repo": repo, "branch": branch, "access_token": token},
        )
        r.raise_for_status()
        return r.json()["report"]


def _slug(s: str, n: int = 40) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "x"


def _finding_signature(kind: str, title: str, file_hint: Optional[str]) -> str:
    """Stable cross-round identifier. Heuristic agents regenerate ids each
    run (e.g. always 'SEC-002') so id alone is too coarse — same id on
    different repos. Title + file is more durable across analyses."""
    return f"{kind}::{(title or '').strip().lower()[:80]}::{(file_hint or '').lower()}"


def _pick_top_per_kind(
    report: Dict[str, Any],
    seen_signatures: set,
    cooled_paths: set,
    parked: set = None,
) -> List[FindingPayload]:
    """Return ≤1 of each kind: guardrail, milestone, blocker, test.

    Skips:
      - any finding whose (kind, title, file) signature was already attempted
        in this loop run (prevents the same heuristic re-firing every round)
      - any finding whose target_file is in `cooled_paths` — files modified
        in an earlier round are likely to re-trigger their own heuristics
        (false positives), so we sit on them for one round
    """
    agents = report.get("agents", {})
    out: List[FindingPayload] = []

    SEV = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    parked = parked or set()
    # Track files about to be hit this round so we don't pick 4 findings
    # that all target backend/app/main.py.
    target_files_used: set = set()

    # Many guardrail findings (CORS, injection, sanitization, secrets,
    # config) have no `finding.file` but Coder's target resolver always
    # picks backend/app/main.py for them. Treat those as implicitly
    # claiming main.py so we don't pick four such findings that all
    # collide on the same file. Same for "ci_cd" findings → ci.yml.
    _MAIN_PY_CATEGORIES = {"cors", "secrets", "auth", "injection",
                            "config", "input_validation"}
    _CI_YAML_CATEGORIES = {"ci_cd"}

    def _eligible(
        kind: str, title: str, file_hint: Optional[str],
        category: Optional[str] = None,
    ) -> bool:
        sig = _finding_signature(kind, title, file_hint)
        if sig in seen_signatures:
            return False
        if sig in parked:
            return False
        if file_hint and file_hint in cooled_paths:
            return False
        if file_hint and file_hint in target_files_used:
            return False
        # Category-implied collision: guardrail/injection (with no explicit
        # file) will be resolved to backend/app/main.py — block if main.py
        # is already taken.
        if not file_hint and _category_implies_main(category):
            if "backend/app/main.py" in target_files_used:
                return False
        return True

    def _claim(file_hint: Optional[str], category: Optional[str] = None) -> None:
        if file_hint:
            target_files_used.add(file_hint)
        cat = (category or "").lower()
        if cat in _MAIN_PY_CATEGORIES:
            target_files_used.add("backend/app/main.py")
        elif cat in _CI_YAML_CATEGORIES:
            target_files_used.add(".github/workflows/ci.yml")

    def _category_implies_main(cat: Optional[str]) -> bool:
        return (cat or "").lower() in _MAIN_PY_CATEGORIES

    # GuardRail
    for f in sorted(
        agents.get("guardrail", {}).get("findings", []) or [],
        key=lambda f: -SEV.get((f.get("severity") or "").lower(), 0),
    ):
        cat = f.get("category")
        if not _eligible("guardrail", f.get("title") or "", f.get("file"), cat):
            continue
        out.append(FindingPayload(
            kind="guardrail", id=f.get("id") or "",
            title=f.get("title") or "",
            description=f.get("description") or "",
            recommendation=f.get("recommendation") or "",
            file=f.get("file"), severity=f.get("severity"),
            category=cat,
        ))
        _claim(f.get("file"), cat)
        break

    # Blocker
    for b in sorted(
        agents.get("plan_forge", {}).get("blockers", []) or [],
        key=lambda b: -SEV.get((b.get("severity") or "").lower(), 0),
    ):
        cat = b.get("category")
        if not _eligible("blocker", b.get("title") or "", None, cat):
            continue
        out.append(FindingPayload(
            kind="blocker",
            id=b.get("id") or _slug(b.get("title") or "blocker"),
            title=b.get("title") or "",
            description=b.get("description") or "",
            recommendation=b.get("resolution") or "",
            severity=b.get("severity"), category=cat,
        ))
        _claim(None, cat)
        break

    # Milestone (feature/tweak — non-testing)
    for m in agents.get("plan_forge", {}).get("milestones", []) or []:
        cat = m.get("category")
        if (cat or "").lower() == "testing":
            continue
        if not _eligible("milestone", m.get("title") or "", None, cat):
            continue
        out.append(FindingPayload(
            kind="milestone",
            id=_slug(m.get("title") or "milestone"),
            title=m.get("title") or "",
            description=m.get("description") or "",
            recommendation="",
            severity=m.get("priority"), category=cat,
        ))
        _claim(None, cat)
        break

    # Test — highest priority, prefer discovery over heuristic. The
    # heuristic fallbacks (test_main, test_error_handling, test_auth_flows)
    # produce universally bad output (vague target, no real assertion to
    # write) so we always skip them.
    _HEURISTIC_TEST_BLOCKLIST = {
        "test_main", "test_error_handling", "test_auth_flows",
        "test_e2e_happy_path", "test_index",
    }
    for t in sorted(
        agents.get("testpilot", {}).get("suggested_tests", []) or [],
        key=lambda t: (
            0 if t.get("source") == "discovery" else 1,
            0 if t.get("target_file") else 1,
            {"high": 0, "medium": 1, "low": 2}.get(
                (t.get("priority") or "").lower(), 3),
        ),
    ):
        if (t.get("name") or "") in _HEURISTIC_TEST_BLOCKLIST:
            continue
        if not _eligible("test", t.get("name") or "", t.get("target_file")):
            continue
        out.append(FindingPayload(
            kind="test",
            id=t.get("name") or _slug(t.get("description") or "test"),
            title=t.get("name") or "",
            description=t.get("description") or "",
            recommendation="",
            file=t.get("target_file"), severity=t.get("priority"),
            category="testing",
        ))
        _claim(t.get("target_file"))
        break

    return out


def _build_repo_lens(report: Dict[str, Any]) -> RepoLensSummary:
    rl = report.get("agents", {}).get("repo_lens", {}) or {}
    return RepoLensSummary(
        primary_language=rl.get("primary_language", "Unknown"),
        tech_stack=rl.get("tech_stack", []) or [],
        entry_points=rl.get("entry_points", []) or [],
        has_ci_cd=rl.get("has_ci_cd", False),
        has_tests=rl.get("has_tests", False),
    )


async def _actuate_one(
    finding: FindingPayload,
    ctx: RepoLensSummary,
    file_tree: List[str],
    token: str,
    owner: str,
    repo: str,
    branch: str,
) -> Dict[str, Any]:
    """Actuate one finding against current state. Returns verdict record."""
    started = time.time()
    rec: Dict[str, Any] = {
        "ts": int(started),
        "finding_kind": finding.kind,
        "finding_id": finding.id,
        "finding_title": finding.title,
        "finding_severity": finding.severity,
        "finding_category": finding.category,
    }
    try:
        target_paths = _resolve_target_paths(finding, ctx, file_tree)
        target_files = await _fetch_current_contents(
            token, owner, repo, target_paths, ref=branch,
        )
        rec["target_paths"] = target_paths

        brief = CoderBrief(
            task=_build_task(finding),
            repo_full_name=f"{owner}/{repo}",
            primary_language=ctx.primary_language,
            tech_stack=ctx.tech_stack,
            entry_points=ctx.entry_points,
            target_files=target_files,
            finding_kind=finding.kind,
            finding_id=finding.id,
            finding_severity=finding.severity,
        )
        agent = CoderAgent()
        coder_out = await asyncio.to_thread(agent.run, brief, _deployment_hint(finding))

        verdict, reasons = _verdict_for(coder_out, target_files, file_tree)
        rec.update({
            "verdict": verdict,
            "reasons": reasons,
            "summary": (coder_out.summary or "")[:600],
            "files": [
                {"path": cf.path, "size": len(cf.new_content), "rationale": cf.rationale}
                for cf in coder_out.files
            ],
            "elapsed_s": round(time.time() - started, 1),
        })
        # Stash the actual file contents on the record so caller can apply.
        rec["_files_full"] = [
            {"path": cf.path, "new_content": cf.new_content}
            for cf in coder_out.files
        ]
    except Exception as e:
        rec.update({
            "verdict": "error",
            "reasons": [str(e)[:300]],
            "elapsed_s": round(time.time() - started, 1),
        })
    return rec


def _snapshot_files(paths: List[str]) -> Dict[str, Optional[str]]:
    """Capture current contents of `paths` so we can revert. None means
    'didn't exist' (and we should delete on revert)."""
    snap: Dict[str, Optional[str]] = {}
    for p in paths:
        full = REPO_ROOT / p
        if full.exists():
            try:
                snap[p] = full.read_text(encoding="utf-8", errors="replace")
            except Exception:
                snap[p] = None
        else:
            snap[p] = None
    return snap


def _restore_snapshot(snap: Dict[str, Optional[str]]) -> None:
    for p, original in snap.items():
        full = REPO_ROOT / p
        if original is None:
            if full.exists():
                full.unlink()
        else:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(original)


def _apply_to_working_tree(
    rec: Dict[str, Any], dry_run: bool = False,
) -> List[str]:
    """Write Coder's output files to local repo. Returns list of touched paths.
    Skips paths that already match (idempotent). Refuses to write outside repo."""
    if dry_run:
        return []
    written: List[str] = []
    for f in rec.get("_files_full", []):
        path = f["path"]
        if path.startswith("/") or ".." in path.split("/"):
            logger.warning("refusing to write suspicious path %s", path)
            continue
        full = REPO_ROOT / path
        try:
            full.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError:
            logger.warning("refusing to write outside repo: %s", path)
            continue
        new_content = f["new_content"]
        if full.exists():
            try:
                if full.read_text(encoding="utf-8", errors="replace") == new_content:
                    continue
            except Exception:
                pass
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(new_content)
        written.append(path)
    return written


# ── Main ─────────────────────────────────────────────────────────────────────

async def run_round(
    round_num: int,
    base_url: str,
    owner: str,
    repo: str,
    branch: str,
    token: str,
    seen_signatures: set,
    cooled_paths: set,
    out_path: Path,
    apply: bool,
    state: Dict[str, Any],
) -> Tuple[int, int, int]:
    """Returns (good_count, bad_count, applied_count).

    `seen_signatures` accumulates (kind+title+file) of every attempted finding
    across all rounds — prevents re-actuating the same surface finding even if
    a heuristic regenerates it next round. `cooled_paths` accumulates files
    we just modified — heuristics often re-fire on our own patches as false
    positives, so we sit on those files for one round.
    """
    print(f"\n{'='*60}\nROUND {round_num}\n{'='*60}")

    print(f"→ Fetching findings…")
    t0 = time.time()
    report = await _fetch_findings(base_url, owner, repo, branch, token)
    print(f"  analyze: {round(time.time()-t0,1)}s — score={report.get('readiness_score')}")

    parked = set(state.get("parked") or [])
    findings = _pick_top_per_kind(report, seen_signatures, cooled_paths, parked)
    if not findings:
        print("  no fresh findings — loop is dry")
        return 0, 0, 0

    # Mark every selected finding as seen IMMEDIATELY so a `bad` verdict
    # doesn't pull the same finding back in next round. This is the fix
    # for the "round 1 and 2 keep showing the same 4 items" bug.
    for f in findings:
        seen_signatures.add(_finding_signature(f.kind, f.title, f.file))

    print(f"  selected {len(findings)} findings:")
    for f in findings:
        print(f"    • [{f.kind}] [{f.severity or '?'}] {f.title[:80]}")

    ctx = _build_repo_lens(report)
    file_tree = await GitHubAPIService.get_file_tree(token, owner, repo, branch)

    # Parallel actuate (≤4 in flight).
    print(f"→ Actuating {len(findings)} in parallel…")
    t0 = time.time()
    recs = await asyncio.gather(*[
        _actuate_one(f, ctx, file_tree, token, owner, repo, branch)
        for f in findings
    ])
    print(f"  actuate: {round(time.time()-t0,1)}s")

    # Refresh cooled_paths each round: only files modified IN THIS round
    # are cooled, not forever — they get a 1-round cooloff.
    cooled_paths.clear()

    # Detect file-collision: two `good` patches both writing the same path.
    # The COMPLETE conflicting patch is dropped (not partially merged), so
    # the next round can re-pick that finding and see the new file state.
    # Earlier kind ordering wins: guardrail > blocker > milestone > test.
    if apply:
        KIND_ORDER = {"guardrail": 0, "blocker": 1, "milestone": 2, "test": 3}
        recs.sort(key=lambda r: KIND_ORDER.get(r.get("finding_kind", "z"), 99))
        seen_paths: set = set()
        for rec in recs:
            if rec.get("verdict") != "good":
                continue
            files = rec.get("_files_full", [])
            paths_in_rec = {f["path"] for f in files}
            collision = paths_in_rec & seen_paths
            if collision:
                # Drop entire patch — partial application is worse than waiting.
                print(f"  ⚠ [{rec['finding_kind']}] DROPPED entire patch (path collision: {collision})")
                rec["_files_full"] = []
                rec.setdefault("reasons", []).append(
                    f"deferred to next round — path collision with earlier patch: {sorted(collision)}"
                )
                # Remove this finding's signature so it can re-actuate next round
                # AGAINST the new file state.
                seen_signatures.discard(_finding_signature(
                    rec["finding_kind"], rec["finding_title"], rec.get("finding_target")
                ))
            else:
                seen_paths.update(paths_in_rec)

    good = bad = applied_count = reverted = 0
    if apply:
        baseline_passing = _baseline_pass_count(state)
        print(f"  baseline tests: {baseline_passing} passing")

    for rec in recs:
        v = rec.get("verdict")
        marker = {"good": "✓", "bad": "✗", "skipped": "—", "error": "!"}.get(v, "?")
        print(f"  {marker} [{rec['finding_kind']}] {rec['finding_title'][:60]} → {v}")
        for r in rec.get("reasons", [])[:2]:
            print(f"      • {r[:140]}")

        if v == "good":
            good += 1
            if apply:
                # Atomic apply: snapshot, write, run tests; if regression,
                # revert and mark `bad`. Skip the gate if Coder produced no
                # files (collision-stripped to empty).
                files = rec.get("_files_full") or []
                if not files:
                    rec.setdefault("reasons", []).append("no files left after collision-strip — skipped apply")
                else:
                    paths = [f["path"] for f in files]
                    snap = _snapshot_files(paths)
                    touched = _apply_to_working_tree(rec)
                    # Fast smoke: import app.main. If this fails we know
                    # pytest will return 0p/Nf and the misleading number
                    # would tank baseline_passing.
                    smoke_ok, smoke_err = _smoke_imports()
                    if not smoke_ok:
                        _restore_snapshot(snap)
                        good -= 1
                        bad += 1
                        reverted += 1
                        rec["verdict"] = "reverted"
                        rec.setdefault("reasons", []).append(
                            f"REVERTED: import smoke failed — {smoke_err[:200]}"
                        )
                        print(f"      ✗ REVERTED — import smoke failed")
                        continue
                    passed, failed, _ = _run_pytest()
                    if passed < baseline_passing:
                        # Regression. Revert.
                        _restore_snapshot(snap)
                        good -= 1
                        bad += 1
                        reverted += 1
                        rec["verdict"] = "reverted"
                        rec.setdefault("reasons", []).append(
                            f"REVERTED: pytest pass count dropped {baseline_passing} → {passed} (failed={failed})"
                        )
                        print(f"      ✗ REVERTED — tests dropped {baseline_passing} → {passed}")
                    else:
                        applied_count += len(touched)
                        baseline_passing = passed  # any improvement becomes new baseline
                        state["baseline_passing"] = passed
                        _save_state(state)
                        if touched:
                            print(f"      → applied {len(touched)} file(s); tests {passed}p/{failed}f")
                        cooled_paths.update(touched)
        elif v == "bad":
            bad += 1

        rec.pop("_files_full", None)
        rec["round"] = round_num
        with out_path.open("a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")

    if reverted:
        print(f"  reverted: {reverted} patch(es) due to test regression")

    # Increment attempt counters for findings that didn't land cleanly.
    # After _MAX_ATTEMPTS consecutive non-`good` rounds, park the finding so
    # the loop stops wasting tokens on it. A successful apply resets it.
    attempts: Dict[str, int] = dict(state.get("attempts") or {})
    parked: List[str] = list(state.get("parked") or [])
    for rec in recs:
        sig = _finding_signature(
            rec["finding_kind"], rec["finding_title"], rec.get("finding_target")
        )
        if rec.get("verdict") == "good" and rec.get("_files_full"):
            attempts.pop(sig, None)
        elif rec.get("verdict") in ("bad", "reverted", "skipped", "error"):
            attempts[sig] = attempts.get(sig, 0) + 1
            if attempts[sig] >= _MAX_ATTEMPTS and sig not in parked:
                parked.append(sig)
                attempts.pop(sig, None)
                print(f"  ⛔ parked (≥{_MAX_ATTEMPTS} failed attempts): {rec['finding_title'][:60]}")
    state["attempts"] = attempts
    state["parked"] = parked
    _save_state(state)

    return good, bad, applied_count


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--owner", default="WalkingDevFlag")
    p.add_argument("--repo", default="Shipmate-AI")
    p.add_argument("--branch", default="feat/bedrock-on-v2")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--out", default="/tmp/coder_loop.jsonl")
    p.add_argument("--rounds", type=int, default=3,
                   help="max rounds; loop also stops early on a dry round")
    p.add_argument("--no-apply", action="store_true",
                   help="skip writing patches to local tree (verdict-only)")
    p.add_argument("--token-from", default="gh")
    p.add_argument("--reset", action="store_true",
                   help="wipe persistent state (seen signatures, baseline)")
    args = p.parse_args()

    if args.token_from == "gh":
        import subprocess
        token = subprocess.check_output(["gh", "auth", "token"]).decode().strip()
    else:
        token = os.environ[args.token_from]

    out_path = Path(args.out)
    out_path.write_text("")

    state = _load_state()
    if getattr(args, "reset", False):
        state = {"seen_signatures": [], "baseline_passing": None}
        _save_state(state)
        print("→ reset persistent state")
    seen_signatures: set = set(state.get("seen_signatures") or [])
    cooled_paths: set = set()
    apply = not args.no_apply
    print(f"Mode: {'APPLY (will modify local working tree)' if apply else 'DRY-RUN (verdicts only)'}")
    print(f"Rounds: up to {args.rounds}")
    if seen_signatures:
        print(f"Loaded {len(seen_signatures)} previously-attempted finding signatures")

    totals = {"good": 0, "bad": 0, "applied": 0}
    for r in range(1, args.rounds + 1):
        try:
            g, b, a = await run_round(
                r, args.base_url, args.owner, args.repo, args.branch,
                token, seen_signatures, cooled_paths, out_path, apply, state,
            )
            # Persist accumulated state across runs.
            state["seen_signatures"] = sorted(seen_signatures)
            _save_state(state)
        except Exception as e:
            print(f"  round {r} crashed: {e}")
            break
        totals["good"] += g
        totals["bad"] += b
        totals["applied"] += a
        if g == 0 and b == 0:
            print("\n  loop is dry — stopping early")
            break

    print(f"\n{'='*60}\nLOOP COMPLETE\n{'='*60}")
    print(f"  good:    {totals['good']}")
    print(f"  bad:     {totals['bad']}")
    print(f"  applied: {totals['applied']} files written to local tree")
    print(f"  log:     {out_path}")
    if apply and totals['applied']:
        print(f"\nReview with:  git diff --stat")
        print(f"Roll back:    git checkout -- backend/ frontend/ .github/")


if __name__ == "__main__":
    asyncio.run(main())
