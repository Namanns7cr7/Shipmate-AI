"""
ShipMate Coder loop harness — DRY-RUN, never opens PRs.

Invokes the full pipeline (analyze → for each finding → CoderAgent →
local quality review) so we can iterate on the Coder prompt without
spamming GitHub with garbage PRs.

Output: JSONL at /tmp/coder_loop.jsonl with one row per finding actuated:
  {finding_kind, finding_id, finding_title, file_count, verdict,
   verdict_reasons, paths, summary, patch_hash, sample_diff}

verdict ∈ {"good", "skipped", "bad", "error"}.

Run:  python -m backend.scripts.coder_loop --owner WalkingDevFlag --repo Shipmate-AI
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

# Allow running as `python backend/scripts/coder_loop.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.agents.coder_agent import CoderAgent, CoderBrief, CoderOutput, CoderFile
from app.schemas.api_schemas import FindingPayload, RepoLensSummary
from app.services.coder_orchestrator import (
    _resolve_target_paths,
    _fetch_current_contents,
    _build_task,
    _deployment_hint,
)
from app.services.github_api_service import GitHubAPIService

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("coder_loop")
logger.setLevel(logging.INFO)

# ── Quality review ───────────────────────────────────────────────────────────

# Patterns that indicate test theater (rule #2 of the system prompt).
_TEST_THEATER_PATTERNS = [
    re.compile(r"status_code\s+in\s*[\(\[][^)\]]*4\d\d", re.MULTILINE),  # accepting 4xx
    re.compile(r"assert\s+(?:isinstance|hasattr)\([^)]*Mock", re.MULTILINE),  # mock asserts
    re.compile(r"FastAPI\(\s*\)", re.MULTILINE),  # hand-rolled FastAPI
    re.compile(r"^app\s*=\s*FastAPI\(\)\s*$", re.MULTILINE),  # mock app pattern
    re.compile(r"\bpyjwt\.encode\b|\bjwt\.encode\b.*assert.*decode", re.MULTILINE | re.DOTALL),  # PyJWT internals
    re.compile(r"^\s*assert\s+True\s*$", re.MULTILINE),  # tautology
    re.compile(r"@pytest\.mark\.skip", re.MULTILINE),
]

# Patterns that look like hallucinated SQL/ORM/DB code.
_HALLUCINATION_DB_PATTERNS = [
    re.compile(r"from\s+sqlalchemy", re.IGNORECASE),
    re.compile(r"from\s+app\.db\.", re.IGNORECASE),
    re.compile(r"declarative_base|sessionmaker", re.IGNORECASE),
]

# Patterns that look like .gitkeep theater — only flag when the .gitkeep
# is inside a directory that the patch claims to remove (e.g. __pycache__/
# or build/) — putting one there preserves the directory you said you'd
# delete. A bare nginx/certs/.gitkeep to bootstrap an empty cert dir is fine.
_GITKEEP_THEATER = re.compile(
    r"(__pycache__|/build|/dist|/\.venv|/node_modules)/[^/]*\.gitkeep$"
)


def _extract_imports(content: str) -> List[str]:
    """Pull `from X import` and `import X` symbols from a Python file."""
    out: List[str] = []
    for m in re.finditer(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", content, re.MULTILINE):
        out.append(m.group(1) or m.group(2))
    return out


def _extract_ts_imports(content: str) -> List[str]:
    """Pull `import X from 'Y'` paths from a TS file."""
    return re.findall(r"from\s+['\"]([^'\"]+)['\"]", content)


def _is_first_party(imp: str) -> bool:
    """Is `imp` a project-internal Python module (vs stdlib/3rd-party)?"""
    return imp.startswith("app.") or imp.startswith("backend.") or imp.startswith(".")


def _check_imports_resolve(
    file_path: str,
    new_content: str,
    target_files: Dict[str, str],
    file_tree: List[str],
) -> List[str]:
    """
    Catch imports of project modules that DON'T exist in the repo.
    Returns list of bad imports (empty list = clean).
    """
    if file_path.endswith((".py",)):
        imports = _extract_imports(new_content)
        bad: List[str] = []
        for imp in imports:
            if not _is_first_party(imp):
                continue
            # Strip `app.` prefix and look for a matching path.
            if imp.startswith("app."):
                rel = "backend/" + imp.replace(".", "/")
            elif imp.startswith("backend."):
                rel = imp.replace(".", "/")
            else:
                continue
            # Match if any file in tree starts with this prefix (could be a module).
            candidates = [
                rel + ".py",
                rel + "/__init__.py",
            ]
            if not any(c in file_tree for c in candidates):
                # Also accept if the import is provided via target_files (Coder may be creating it).
                created = any(
                    cf for cf in target_files
                    if cf.endswith(rel.split("/")[-1] + ".py")
                )
                if not created:
                    bad.append(imp)
        return bad
    return []


def _detect_test_theater(content: str) -> List[str]:
    hits: List[str] = []
    for pat in _TEST_THEATER_PATTERNS:
        if pat.search(content):
            hits.append(pat.pattern[:60])
    return hits


def _looks_like_test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith(".test.tsx") or name.endswith(".test.ts") or "tests/" in path or "__tests__/" in path


def _verdict_for_file(
    cf: CoderFile,
    target_files: Dict[str, str],
    file_tree: List[str],
    finding: FindingPayload,
) -> Tuple[str, List[str]]:
    """Returns (verdict, reasons) for a single CoderFile."""
    reasons: List[str] = []

    # 1. Empty/trivial new content?
    if len(cf.new_content.strip()) < 20:
        return "bad", ["file content is empty/trivial (<20 chars)"]

    # 2. .gitkeep theater?
    if _GITKEEP_THEATER.search(cf.path):
        return "bad", [".gitkeep theater pattern"]

    # 3. Hallucinated imports (Python only)?
    bad_imports = _check_imports_resolve(cf.path, cf.new_content, target_files, file_tree)
    if bad_imports:
        reasons.append(f"hallucinated imports: {bad_imports[:5]}")

    # 4. Test theater?
    if _looks_like_test_file(cf.path):
        theater = _detect_test_theater(cf.new_content)
        if theater:
            reasons.append(f"test theater patterns: {theater[:3]}")
        # Tests must reference at least one project-internal import.
        if cf.path.endswith(".py"):
            imps = _extract_imports(cf.new_content)
            first_party = [i for i in imps if _is_first_party(i)]
            if not first_party:
                reasons.append("test does not import any project module — likely tests library internals")

    # 5. Database imports w/o the manifest containing the dep — but ONLY
    # flag NEW imports that weren't in the original. If the file already
    # had them, Coder isn't the one introducing the issue.
    original = target_files.get(cf.path, "")
    new_db_imports = [
        p.pattern for p in _HALLUCINATION_DB_PATTERNS
        if p.search(cf.new_content) and not p.search(original)
    ]
    if new_db_imports:
        reqs_blob = (
            target_files.get("backend/requirements.txt", "")
            + target_files.get("requirements.txt", "")
            + target_files.get("backend/pyproject.toml", "")
        )
        if "sqlalchemy" not in reqs_blob.lower():
            reasons.append(
                "introduces NEW db/SQLAlchemy import without adding manifest update: "
                f"{new_db_imports}"
            )

    # 6. Scope discipline — patch unrelated to finding category?
    # NOTE: security finding + test-only file is ONLY scope-drift if Coder
    # didn't also include or skip a corresponding production file. The caller
    # checks across all files in the output to make that judgement.

    if reasons:
        return "bad", reasons
    return "good", []


def _verdict_for_output(
    coder_out: CoderOutput,
    target_files: Dict[str, str],
    file_tree: List[str],
    finding: FindingPayload,
) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """
    Returns (overall_verdict, reasons, per_file_records).
    overall is "bad" if ANY file is bad. "good" if all good.
    """
    if not coder_out.files:
        return "skipped", ["coder produced 0 files"], []

    per_file: List[Dict[str, Any]] = []
    overall_reasons: List[str] = []
    any_bad = False
    for cf in coder_out.files:
        v, rs = _verdict_for_file(cf, target_files, file_tree, finding)
        per_file.append({
            "path": cf.path,
            "verdict": v,
            "reasons": rs,
            "size": len(cf.new_content),
            "rationale": cf.rationale,
        })
        if v == "bad":
            any_bad = True
            overall_reasons.append(f"{cf.path}: {rs[0]}")

    # VERIFY-line check
    if "VERIFY:" not in (coder_out.summary or ""):
        overall_reasons.append("summary missing required 'VERIFY:' self-check line")
        any_bad = True

    return ("bad" if any_bad else "good"), overall_reasons, per_file


# ── Main loop ────────────────────────────────────────────────────────────────

async def _fetch_findings(
    base_url: str, owner: str, repo: str, branch: str, token: str,
) -> Dict[str, Any]:
    """Call /api/analyze and return the report."""
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"{base_url}/api/analyze",
            json={"owner": owner, "repo": repo, "branch": branch, "access_token": token},
        )
        r.raise_for_status()
        return r.json()["report"]


def _flatten_findings(report: Dict[str, Any]) -> List[FindingPayload]:
    """Convert all actuatable items in a report to FindingPayload objects."""
    out: List[FindingPayload] = []
    agents = report.get("agents", {})

    for f in agents.get("guardrail", {}).get("findings", []) or []:
        out.append(FindingPayload(
            kind="guardrail",
            id=f.get("id") or "",
            title=f.get("title") or "",
            description=f.get("description") or "",
            recommendation=f.get("recommendation") or "",
            file=f.get("file"),
            severity=f.get("severity"),
            category=f.get("category"),
        ))

    for m in agents.get("plan_forge", {}).get("milestones", []) or []:
        out.append(FindingPayload(
            kind="milestone",
            id=re.sub(r"[^a-zA-Z0-9]+", "-", (m.get("title") or "").lower()).strip("-")[:40] or "milestone",
            title=m.get("title") or "",
            description=m.get("description") or "",
            recommendation="",
            severity=m.get("priority"),
            category=m.get("category"),
        ))

    for b in agents.get("plan_forge", {}).get("blockers", []) or []:
        out.append(FindingPayload(
            kind="blocker",
            id=b.get("id") or re.sub(r"[^a-zA-Z0-9]+", "-", (b.get("title") or "").lower()).strip("-")[:40],
            title=b.get("title") or "",
            description=b.get("description") or "",
            recommendation=b.get("resolution") or "",
            severity=b.get("severity"),
            category=b.get("category"),
        ))

    for t in agents.get("testpilot", {}).get("suggested_tests", []) or []:
        out.append(FindingPayload(
            kind="test",
            id=t.get("name") or "",
            title=t.get("name") or "",
            description=t.get("description") or "",
            recommendation="",
            file=t.get("target_file"),
            severity=t.get("priority"),
            category="testing",
        ))

    return out


def _build_repo_lens_summary(report: Dict[str, Any]) -> RepoLensSummary:
    rl = report.get("agents", {}).get("repo_lens", {}) or {}
    return RepoLensSummary(
        primary_language=rl.get("primary_language", "Unknown"),
        tech_stack=rl.get("tech_stack", []) or [],
        entry_points=rl.get("entry_points", []) or [],
        has_ci_cd=rl.get("has_ci_cd", False),
        has_tests=rl.get("has_tests", False),
    )


async def _drive_one(
    finding: FindingPayload,
    ctx: RepoLensSummary,
    file_tree: List[str],
    token: str,
    owner: str,
    repo: str,
    branch: str,
) -> Dict[str, Any]:
    """Run Coder for one finding and return a verdict record."""
    started = time.time()
    record: Dict[str, Any] = {
        "ts": int(started),
        "finding_kind": finding.kind,
        "finding_id": finding.id,
        "finding_title": finding.title,
        "finding_severity": finding.severity,
        "finding_category": finding.category,
    }

    try:
        target_paths = _resolve_target_paths(finding, ctx, file_tree)
        record["resolved_paths"] = target_paths

        target_files = await _fetch_current_contents(
            token, owner, repo, target_paths, ref=branch,
        )
        record["target_file_sizes"] = {p: len(c) for p, c in target_files.items()}

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

        verdict, reasons, per_file = _verdict_for_output(
            coder_out, target_files, file_tree, finding,
        )

        # Sample first 800 chars of first file to make manual review easy.
        sample = ""
        if coder_out.files:
            sample = coder_out.files[0].new_content[:800]

        patch_hash = hashlib.sha256(
            "|".join(f"{f.path}:{f.new_content}" for f in coder_out.files).encode()
        ).hexdigest()[:12]

        record.update({
            "verdict": verdict,
            "reasons": reasons,
            "per_file": per_file,
            "summary": coder_out.summary[:600],
            "skipped": coder_out.skipped,
            "patch_hash": patch_hash,
            "sample": sample,
            "elapsed_s": round(time.time() - started, 1),
        })
    except Exception as e:
        record.update({
            "verdict": "error",
            "reasons": [str(e)[:300]],
            "elapsed_s": round(time.time() - started, 1),
        })
    return record


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--owner", default="WalkingDevFlag")
    p.add_argument("--repo", default="Shipmate-AI")
    p.add_argument("--branch", default="main")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--out", default="/tmp/coder_loop.jsonl")
    p.add_argument("--max", type=int, default=20, help="cap on findings to actuate")
    p.add_argument("--token-from", default="gh", help="`gh` to use gh auth token, or env var name")
    args = p.parse_args()

    if args.token_from == "gh":
        import subprocess
        token = subprocess.check_output(["gh", "auth", "token"]).decode().strip()
    else:
        token = os.environ[args.token_from]

    print(f"→ Fetching report for {args.owner}/{args.repo}@{args.branch}…")
    report = await _fetch_findings(args.base_url, args.owner, args.repo, args.branch, token)
    findings = _flatten_findings(report)
    ctx = _build_repo_lens_summary(report)
    print(f"  found {len(findings)} actuatable items")

    file_tree = await GitHubAPIService.get_file_tree(token, args.owner, args.repo, args.branch)
    print(f"  fetched {len(file_tree)} files in tree")

    findings = findings[: args.max]

    rows: List[Dict[str, Any]] = []
    out_path = Path(args.out)
    out_path.write_text("")  # truncate

    for i, f in enumerate(findings, 1):
        print(f"\n[{i}/{len(findings)}] {f.kind}/{f.id} — {f.title[:70]}")
        rec = await _drive_one(f, ctx, file_tree, token, args.owner, args.repo, args.branch)
        rows.append(rec)
        with out_path.open("a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        v = rec.get("verdict")
        marker = {"good": "✓", "bad": "✗", "error": "!", "skipped": "—"}.get(v, "?")
        print(f"  {marker} verdict={v} files={len(rec.get('per_file', []))} elapsed={rec.get('elapsed_s')}s")
        if rec.get("reasons"):
            for r in rec["reasons"][:3]:
                print(f"     • {r[:120]}")

    # Aggregate
    counts: Dict[str, int] = {}
    for r in rows:
        v = r.get("verdict") or "?"
        counts[v] = counts.get(v, 0) + 1
    print(f"\n=== SUMMARY ({len(rows)} findings actuated) ===")
    for k, n in counts.items():
        print(f"  {k:8s}: {n}")
    print(f"\nFull JSONL → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
