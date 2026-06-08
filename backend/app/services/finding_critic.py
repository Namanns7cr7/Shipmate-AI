"""
FindingCritic — verifies and suppresses diagnostic findings before they surface.

Two responsibilities, both aimed at the harness's chronic weakness (noisy,
recurring, sometimes-wrong findings):

  1. VERIFY (the critic pass): an independent LLM pass re-reads each candidate
     finding against the EXACT code that was sent to the agent and votes on
     whether it is real, citing evidence. Findings that the critic refutes are
     dropped. This is the automated form of the manual audit that repeatedly
     caught GuardRail flagging its own anti-injection regexes.

  2. SUPPRESS (journal-aware): findings the user already dismissed — or that
     were already shipped — are filtered out using the shared finding_journal
     (kind::title::file signatures). The diagnostic agents never consulted the
     journal before, which is exactly why dismissed findings recurred every run.

Both are best-effort and fail-open on the SUPPRESS side (a journal/DB hiccup
must never hide a finding) and fail-open on the VERIFY side too (if the critic
LLM is unavailable, we keep the finding rather than silently dropping it — a
false positive is annoying, a hidden real issue is dangerous).

The signature scheme MUST stay in lockstep with
coder_orchestrator._finding_signature / coder_loop._finding_signature /
findings route — `kind::title::file`, lowercased, title capped at 80 chars.
"""
from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("shipmate.finding_critic")

# States in the journal that mean "do not surface this finding again".
_SUPPRESSED_STATES = ("dismissed", "shipped")

# Critic is on by default but killable via env (e.g. to A/B its effect or when
# token budget is tight). The suppression pass is always on (it's free + local).
_CRITIC_ENABLED = os.getenv("SHIPMATE_FINDING_CRITIC", "1").strip().lower() not in ("0", "false", "no")


def finding_signature(kind: str, title: str, file: Optional[str]) -> str:
    """Canonical kind::title::file signature. MUST match
    coder_orchestrator._finding_signature, coder_loop._finding_signature, and
    the findings route — a finding identified on any surface maps to one row."""
    t = (title or "").strip().lower()[:80]
    f = (file or "").lower()
    return f"{kind}::{t}::{f}"


# ── Suppression (journal-aware) ──────────────────────────────────────────────

def suppressed_signatures(repo_full_name: str) -> set:
    """Set of signatures the user dismissed or already shipped for this repo.
    Empty set on any error (fail-open: never hide a finding because the DB
    hiccuped)."""
    if not repo_full_name:
        return set()
    try:
        from app.services import inflight_registry as ir
        rows = ir.journal_list(
            repo_full_name=repo_full_name, state_in=list(_SUPPRESSED_STATES)
        )
        return {r["finding_sig"] for r in rows}
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("suppressed_signatures lookup failed (%s); suppressing nothing", e)
        return set()


def filter_suppressed(findings: List[Any], kind: str, repo_full_name: str) -> List[Any]:
    """Drop findings whose signature is dismissed/shipped in the journal.

    `findings` are objects with .title and (optionally) .file attributes — the
    SecurityFinding / Blocker / SuggestedTest shapes. `kind` is the agent kind
    used in the signature (e.g. 'guardrail'). Order preserved."""
    suppressed = suppressed_signatures(repo_full_name)
    if not suppressed:
        return findings
    kept = []
    for f in findings:
        sig = finding_signature(
            kind, getattr(f, "title", "") or "", getattr(f, "file", None)
        )
        if sig in suppressed:
            logger.info("suppressing journaled finding: %s", sig)
            continue
        kept.append(f)
    return kept


# ── Verification (the critic pass) ───────────────────────────────────────────

class _Verdict(BaseModel):
    title: str = Field(..., description="The finding title being judged, verbatim.")
    is_real: bool = Field(..., description="True only if the finding is a genuine issue in the code shown.")
    reason: str = Field(..., description="One sentence citing the specific evidence (or why it's a false positive).")


class _CriticReport(BaseModel):
    verdicts: List[_Verdict] = Field(default_factory=list)


_CRITIC_SYSTEM = (
    "You are a skeptical senior security/code reviewer acting as a VERIFIER for "
    "an automated analysis tool that is KNOWN to produce false positives. You "
    "are given (a) the exact source code that was analyzed and (b) candidate "
    "findings. Your ONE job is to catch false positives. Be aggressive about it.\n\n"
    "Mark is_real=FALSE (the finding is bogus) when ANY of these hold:\n"
    "  1. DETECTION/DEFENSIVE CODE: the flagged token only appears inside a "
    "regex literal, a denylist/blocklist, a sanitiser, a comment, a docstring, "
    "a string constant, or a SECURITY CHECK. Code that BLOCKS or DETECTS a "
    "pattern is the OPPOSITE of being vulnerable to it.\n"
    "  2. The control the finding says is MISSING actually EXISTS in the code "
    "shown (e.g. 'no body sanitization' but a sanitize middleware is present; "
    "'OAuth state in-memory' but a sqlite/db store is present; 'no auth check' "
    "but a verify_*_access call is present).\n"
    "  3. Generic boilerplate not grounded in the specific code shown.\n"
    "  4. References a file/line/symbol that does not appear in the code shown.\n\n"
    "WORKED EXAMPLE (critical — this exact case recurs):\n"
    "  Finding: 'Dynamic code execution detected — eval()/exec()/__import__()'.\n"
    "  Code shown contains only:  _DANGEROUS_PATTERNS = [re.compile(r\"eval\\\\s*\\\\(\"), "
    "re.compile(r\"exec\\\\s*\\\\(\"), re.compile(r\"__import__\\\\s*\\\\(\")] used by a "
    "middleware that returns HTTP 400 on a match.\n"
    "  CORRECT VERDICT: is_real=FALSE. These are detection regexes that BLOCK "
    "eval/exec; there is no actual eval()/exec() CALL. Flagging them is the "
    "tool flagging its own defense. Only is_real=TRUE if you can point to a "
    "real call like `result = eval(user_input)` at a code (non-string, "
    "non-comment, non-regex) position.\n\n"
    "Set is_real=TRUE only when you can quote the concrete offending line and it "
    "is genuine executable code, not a pattern/string/comment. When in doubt "
    "about whether it's defensive code, prefer is_real=FALSE. Emit exactly one "
    "verdict per finding, echoing the title verbatim."
)


def _is_injection_finding(f: Any) -> bool:
    cat = (getattr(f, "category", "") or "").lower()
    title = (getattr(f, "title", "") or "").lower()
    return cat == "injection" or "dynamic code execution" in title or "eval" in title


def _deterministic_prefilter(findings: List[Any], code_blob: str) -> List[Any]:
    """Drop findings we can refute WITHOUT an LLM. Currently: a dynamic-code-
    execution / injection finding is refuted when the code-aware detector finds
    no genuine eval/exec/__import__ CALL in the analyzed code (i.e. the matches
    are only regex literals / denylist strings / comments). This is the reliable
    fix for the recurring false positive; the LLM critic is too conservative to
    drop a security finding on its own. Fail-open: if we can't decide, keep it."""
    if not code_blob:
        return findings
    try:
        # Lazy import to avoid a cycle (guardrail_agent imports llm_service which
        # could import this module).
        from app.agents.guardrail_agent import _has_real_dynamic_exec
    except Exception:
        return findings
    real_exec = _has_real_dynamic_exec(code_blob)
    kept = []
    for f in findings:
        if _is_injection_finding(f) and not real_exec:
            logger.info(
                "deterministic prefilter refuted injection finding (no real "
                "eval/exec call in analyzed code): %s", getattr(f, "title", ""),
            )
            continue
        kept.append(f)
    return kept


def verify_findings(
    findings: List[Any],
    code_blob: str,
    provider: Any,
    deployment_hint: str = "smart",
) -> List[Any]:
    """Run the critic pass: keep only findings the verifier confirms as real.

    `findings` are objects with .title and .description. `code_blob` is the
    exact source that was analyzed (so the critic judges against the same
    evidence). `provider` is an LLM provider (or None). Fail-open: on any error
    or if the critic is disabled / provider missing, return findings unchanged
    — never silently drop a finding because the critic couldn't run."""
    if not findings:
        return findings

    # Deterministic pre-filter (runs even with no LLM): for the categories we
    # can verify programmatically, drop a finding when the code-aware detector
    # says the pattern is NOT genuinely present. This is what reliably kills the
    # recurring "dynamic code execution" false positive that the LLM critic is
    # too conservative to refute — main.py's eval/exec regex LITERALS are not a
    # real call, and _has_real_dynamic_exec() returns False for them.
    findings = _deterministic_prefilter(findings, code_blob)

    if not _CRITIC_ENABLED or provider is None or not findings:
        return findings

    try:
        listing = "\n".join(
            f"{i + 1}. [{getattr(f, 'severity', '')}] {getattr(f, 'title', '')}: "
            f"{(getattr(f, 'description', '') or '')[:300]}"
            for i, f in enumerate(findings)
        )
        user = (
            "## Source code that was analyzed\n"
            f"{code_blob[:24000]}\n\n"
            "## Candidate findings to verify\n"
            f"{listing}\n\n"
            "Emit one verdict per finding (is_real + one-sentence reason), title verbatim."
        )
        report = provider.invoke_structured_sync(
            system_prompt=_CRITIC_SYSTEM,
            user_prompt=user,
            schema_class=_CriticReport,
            deployment_hint=deployment_hint,
        )
        # Map verdicts back by normalized title. Unknown/unmatched findings are
        # KEPT (fail-open) — only an explicit is_real=false drops a finding.
        refuted = {
            (v.title or "").strip().lower()
            for v in report.verdicts
            if v.is_real is False
        }
        if not refuted:
            return findings
        kept = []
        for f in findings:
            if (getattr(f, "title", "") or "").strip().lower() in refuted:
                logger.info("critic refuted finding: %s", getattr(f, "title", ""))
                continue
            kept.append(f)
        return kept
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("critic pass failed (%s); keeping all findings", e)
        return findings


# ── Fix-resolution check ─────────────────────────────────────────────────────
# 'shipped' must mean the finding is actually GONE, not merely 'CI went green'.
# For finding kinds that map to a detectable pattern, re-scan the patched
# content: if the offending pattern STILL matches, the patch didn't resolve it.
# This is a cheap, deterministic signal layered under the pytest/lint gate.

# kind/category -> regex that, if STILL present in the new content, means the
# issue persists. Conservative: only kinds we can detect reliably. Anything not
# listed returns 'unknown' (we don't block — fail-open).
import re as _re

_RESOLUTION_PATTERNS = {
    "injection": _re.compile(r"(?<![\"'`\w.])(?:eval|exec|__import__)\s*\(", _re.IGNORECASE),
    "secrets": _re.compile(r"(?i)(?:api[_-]?key|secret|password|token)\s*=\s*[\"'][^\"']{8,}[\"']"),
}


def is_finding_resolved(category: str, new_contents: List[str]) -> Optional[bool]:
    """Return True if the finding's pattern is GONE from the patched content,
    False if it still matches, or None when the category isn't deterministically
    checkable (caller should fall back to the test/lint gate, not block).

    `new_contents` is the list of patched file bodies the Coder produced."""
    pattern = _RESOLUTION_PATTERNS.get((category or "").lower())
    if pattern is None:
        return None
    blob = "\n".join(c for c in new_contents if c)
    # Scan only non-comment, non-defensive lines — same spirit as the GuardRail
    # detector: a comment or regex literal mentioning the token isn't the issue.
    for raw in blob.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "`" in line:
            continue
        low = line.lower()
        if any(m in low for m in ("re.compile", "denylist", "blocklist", "pattern", "sanitiz")):
            continue
        if pattern.search(line):
            return False  # the offending pattern is still present
    return True
