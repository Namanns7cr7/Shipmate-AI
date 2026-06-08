"""
OpportunityCritic — grounds, suppresses, and ranks self-improvement opportunities.

This is the Phase-1A gate that decides whether ShipMate's "what should we build
next" picks are GOOD. It is modelled on finding_critic.py but tuned for
opportunities (features / improvements / tweaks / bugs) rather than security
findings. Three responsibilities, all deterministic + fail-open:

  1. GROUND (deterministic, no LLM): an opportunity is only trustworthy if its
     cited `evidence` / `target_files` point at files that actually exist in the
     repo. We verify each evidence string against the known file set. An
     opportunity with zero verifiable evidence is marked grounded=False and
     dropped from the default view — this is the reliable defense against the
     model hallucinating plausible-but-fake work (the exact failure mode the
     finding_critic deterministic prefilter was built to catch).

  2. SUPPRESS (journal-aware): opportunities the user dismissed — or that were
     already shipped — are filtered using the shared finding_journal, keyed by
     an `opportunity::`-PREFIXED signature. The prefix matters: suppressed_*
     reuse would mix opportunity sigs with guardrail/blocker sigs. We filter to
     the opportunity namespace explicitly so the two never cross-suppress.

  3. RANK (folded in, deterministic): a value_score (0-100) from category,
     effort, impact signal, and grounding strength — then DOWNRANK anything
     already in_progress so a plan-only run surfaces the NEXT idea instead of
     re-suggesting the one you just clicked. Sorted desc; priority derived.

The signature scheme MUST stay in lockstep with finding_critic.finding_signature
/ coder_orchestrator._finding_signature — `kind::title::file`, lowercased, title
capped at 80 chars — except `kind` is the literal "opportunity".
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("shipmate.opportunity_critic")

# The journal `kind` for opportunities. Keeping it a distinct namespace from
# guardrail/blocker/test sigs is what prevents cross-suppression.
OPPORTUNITY_KIND = "opportunity"

# Journal states that mean "do not surface this opportunity again".
_SUPPRESSED_STATES = ("dismissed", "shipped")

# in_progress opportunities aren't suppressed (you may want to see one you're
# mid-build on) but they ARE downranked so the next plan-only run advances to
# fresh work instead of re-topping the one already being built.
_INPROGRESS_PENALTY = 40


def opportunity_signature(title: str, file: Optional[str] = None) -> str:
    """Canonical `opportunity::title::file` signature. Mirrors
    finding_critic.finding_signature but pinned to the opportunity namespace.
    `file` is the first target_file (or evidence path) so the same opportunity
    maps to one journal row regardless of how it's re-discovered."""
    t = (title or "").strip().lower()[:80]
    f = (file or "").lower()
    return f"{OPPORTUNITY_KIND}::{t}::{f}"


def _primary_file(opp: Any) -> str:
    """The file an opportunity's signature is keyed on: first target_file, else
    first evidence path, else empty (title-only signature)."""
    tf = getattr(opp, "target_files", None) or []
    if tf:
        return tf[0]
    ev = getattr(opp, "evidence", None) or []
    return ev[0] if ev else ""


# ── Grounding (deterministic — the reliable quality gate) ────────────────────

def _known_paths(file_tree: List[str], key_files: Dict[str, str]) -> Set[str]:
    """All path-ish strings we can verify against: the full tree plus any
    path-keyed entries in key_files. Lowercased for case-insensitive matching."""
    paths: Set[str] = set()
    for p in file_tree or []:
        if p:
            paths.add(p.lower())
    for k in (key_files or {}).keys():
        if k:
            paths.add(k.lower())
    return paths


def _evidence_is_grounded(evidence_item: str, known: Set[str]) -> bool:
    """True when an evidence/target string references a file that exists.

    Evidence is free text like
    'backend/app/services/repo_analysis_service.py:_fetch_files — no caching'.
    We extract the leading path token (before ':' / whitespace / '—') and check
    it against the known path set with a forgiving suffix match (the tree may
    store 'src/foo.py' while evidence cites 'frontend/src/foo.py' or vice
    versa). Bias toward accepting a real-looking path so we don't over-drop —
    the LLM is explicitly told to cite real files, and a borderline path is
    less harmful than silently discarding a good opportunity."""
    if not evidence_item:
        return False
    # Take the leading path token: everything up to the FIRST of whitespace,
    # ':', em/en-dash, '#', or '(' — whichever comes earliest. We deliberately
    # do NOT split on '-' because real filenames contain it (docker-compose.yml).
    head = re.split(r"[\s:—–#(]", evidence_item.strip(), maxsplit=1)[0]
    head = head.strip().strip(",.;").lower()
    if not head or ("/" not in head and "." not in head):
        # Not path-shaped (e.g. a bare function name) — can't verify, don't count.
        return False
    if head in known:
        return True
    # Suffix / containment match: 'repo_analysis_service.py' should match
    # 'backend/app/services/repo_analysis_service.py'.
    base = head.split("/")[-1]
    for kp in known:
        if kp == head or kp.endswith("/" + head) or kp.endswith("/" + base) or kp == base:
            return True
    return False


def ground_opportunities(
    opportunities: List[Any],
    file_tree: List[str],
    key_files: Optional[Dict[str, str]] = None,
) -> List[Any]:
    """Set `grounded` on each opportunity based on whether its evidence /
    target_files cite real repo paths. Mutates and returns the list (order
    preserved). Fail-open: if we have no file tree to check against, mark
    everything grounded (we can't disprove it) rather than dropping all."""
    known = _known_paths(file_tree or [], key_files or {})
    if not known:
        for opp in opportunities:
            try:
                opp.grounded = True
            except Exception:
                pass
        return opportunities

    for opp in opportunities:
        candidates = list(getattr(opp, "evidence", None) or []) + \
                     list(getattr(opp, "target_files", None) or [])
        grounded = any(_evidence_is_grounded(c, known) for c in candidates)
        try:
            opp.grounded = bool(grounded)
        except Exception:
            pass
        if not grounded:
            logger.info(
                "opportunity not grounded (no cited path exists in repo): %s",
                getattr(opp, "title", ""),
            )
    return opportunities


# ── Suppression (journal-aware, opportunity-namespaced) ──────────────────────

def suppressed_opportunity_signatures(repo_full_name: str) -> Set[str]:
    """Set of opportunity signatures dismissed/shipped for this repo. Filters to
    the `opportunity::` namespace so guardrail/blocker sigs can never suppress
    an opportunity (and vice-versa). Empty set on any error (fail-open)."""
    if not repo_full_name:
        return set()
    try:
        from app.services import inflight_registry as ir
        rows = ir.journal_list(
            repo_full_name=repo_full_name, state_in=list(_SUPPRESSED_STATES)
        )
        return {
            r["finding_sig"] for r in rows
            if str(r.get("finding_sig", "")).startswith(OPPORTUNITY_KIND + "::")
        }
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("suppressed_opportunity_signatures failed (%s); suppressing nothing", e)
        return set()


def journal_states_for(repo_full_name: str) -> Dict[str, str]:
    """Map of opportunity_signature -> state for ALL journal rows in the
    opportunity namespace (any state). Used to annotate + downrank in_progress.
    Empty on error."""
    if not repo_full_name:
        return {}
    try:
        from app.services import inflight_registry as ir
        rows = ir.journal_list(repo_full_name=repo_full_name)
        return {
            r["finding_sig"]: r["state"] for r in rows
            if str(r.get("finding_sig", "")).startswith(OPPORTUNITY_KIND + "::")
        }
    except Exception as e:  # pragma: no cover - defensive
        logger.debug("journal_states_for failed (%s)", e)
        return {}


def filter_suppressed(opportunities: List[Any], repo_full_name: str) -> List[Any]:
    """Drop opportunities whose signature is dismissed/shipped in the journal.
    Order preserved. Fail-open: empty suppression set returns the list as-is."""
    suppressed = suppressed_opportunity_signatures(repo_full_name)
    if not suppressed:
        return opportunities
    kept = []
    for opp in opportunities:
        sig = opportunity_signature(getattr(opp, "title", "") or "", _primary_file(opp))
        if sig in suppressed:
            logger.info("suppressing journaled opportunity: %s", sig)
            continue
        kept.append(opp)
    return kept


# ── Ranking (folded in — deterministic value model) ──────────────────────────

# Category weight: bugs and high-leverage improvements rank above net-new
# features (cheaper to land, lower risk) but features still score respectably.
_CATEGORY_WEIGHT = {"bug": 30, "improvement": 26, "tweak": 18, "feature": 22}
# Effort weight: smaller = sooner. S beats L for the same value.
_EFFORT_WEIGHT = {"S": 22, "M": 14, "L": 6}

# Impact phrases that signal real, measurable leverage — a light keyword bump so
# "cuts latency"/"reduces API calls" outranks vague "improves things".
_IMPACT_SIGNALS = (
    "latency", "perf", "faster", "speed", "cache", "reduce", "fewer",
    "reliab", "crash", "data loss", "security", "leak", "cost", "coverage",
    "uptime", "throughput", "memory", "race", "timeout", "retry",
)


def _value_score(opp: Any) -> int:
    """0-100 value score. Higher ⇒ ship sooner. Deterministic + explainable.

    Grounding is NOT a bonus here — it's the drop-gate (ungrounded items are
    removed before ranking by default), so adding a flat +N to every survivor
    would just inflate all scores into one bucket. We only PENALISE ungrounded
    items (relevant when include_ungrounded keeps them for debugging) so they
    sink below every grounded pick. The discriminating signal comes from
    category + effort + evidence depth + impact wording."""
    score = 0
    cat = (getattr(opp, "category", "") or "").lower()
    score += _CATEGORY_WEIGHT.get(cat, 18)        # 18-30

    eff = (getattr(opp, "effort", "") or "").upper()
    score += _EFFORT_WEIGHT.get(eff, 12)          # 6-22

    # Evidence depth: more cited real files ⇒ more trustworthy.
    n_evidence = len(getattr(opp, "evidence", None) or [])
    score += min(15, n_evidence * 5)              # 0-15

    # Impact signal keywords (measurable leverage).
    impact = (getattr(opp, "impact", "") or "").lower()
    if any(sig in impact for sig in _IMPACT_SIGNALS):
        score += 12

    # A concrete suggested approach (semi-plan) is a small confidence bump.
    if (getattr(opp, "suggested_approach", None) or []):
        score += 6

    # Ungrounded penalty (only ever hit when include_ungrounded keeps them).
    if not getattr(opp, "grounded", True):
        score -= 30

    return max(0, min(100, score))


def _priority_for(value_score: int) -> str:
    # Calibrated to the real distribution of grounded items (~24-85): only the
    # genuinely top-tier picks earn "critical", so the label stays meaningful.
    if value_score >= 72:
        return "critical"
    if value_score >= 55:
        return "high"
    if value_score >= 38:
        return "medium"
    return "low"


def rank_opportunities(
    opportunities: List[Any],
    repo_full_name: str = "",
    *,
    drop_ungrounded: bool = True,
) -> List[Any]:
    """Score, annotate journal_state, downrank in_progress, sort desc, derive
    priority. With `drop_ungrounded` (default), ungrounded opportunities are
    removed entirely — the plan-only view should show only trustworthy picks.

    Returns a NEW sorted list; input objects are mutated in place with
    value_score / priority / journal_state."""
    states = journal_states_for(repo_full_name) if repo_full_name else {}

    scored: List[Any] = []
    for opp in opportunities:
        if drop_ungrounded and not getattr(opp, "grounded", True):
            continue
        base = _value_score(opp)
        sig = opportunity_signature(getattr(opp, "title", "") or "", _primary_file(opp))
        state = states.get(sig)
        try:
            opp.journal_state = state
        except Exception:
            pass
        if state == "in_progress":
            base = max(0, base - _INPROGRESS_PENALTY)
        try:
            opp.value_score = base
            opp.priority = _priority_for(base)
        except Exception:
            pass
        scored.append(opp)

    scored.sort(key=lambda o: getattr(o, "value_score", 0), reverse=True)
    # Re-id in rank order so OPP-001 is the top pick the UI shows first.
    for i, opp in enumerate(scored, start=1):
        try:
            opp.id = f"OPP-{i:03d}"
        except Exception:
            pass
    return scored
