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

from pydantic import BaseModel, Field

logger = logging.getLogger("shipmate.opportunity_critic")

# The LLM verify pass (Phase 1B) is on by default but killable via env, exactly
# like finding_critic's _CRITIC_ENABLED. The deterministic grounding/suppression
# /ranking passes are always on (free + local).
_VERIFY_ENABLED = os.getenv("SHIPMATE_OPPORTUNITY_VERIFY", "1").strip().lower() not in ("0", "false", "no")

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


# ── Verification (the LLM critic pass — catches "already built") ─────────────
# Phase 1B. The smoke run proved deterministic grounding is necessary but not
# sufficient: an opportunity can cite REAL files (grounded=True) yet propose
# work that's ALREADY DONE — e.g. "persist reports for history" when
# report_store.py + the /history endpoint already exist. Grounding can't catch
# that; only reading the code can. This is the direct analogue of
# finding_critic's "the control the finding says is MISSING actually EXISTS"
# rule, applied to build opportunities.

class _OppVerdict(BaseModel):
    title: str = Field(..., description="The opportunity title being judged, verbatim.")
    worth_doing: bool = Field(..., description="False if the work already exists, is a duplicate, or is not actually an improvement given the code shown.")
    reason: str = Field(..., description="One sentence citing specific evidence (the existing implementation, or why it's still worth doing).")


class _OppCriticReport(BaseModel):
    verdicts: List[_OppVerdict] = Field(default_factory=list)


_VERIFY_SYSTEM = (
    "You are a skeptical staff engineer acting as a VERIFIER for an automated "
    "tool that proposes 'self-improvement opportunities' for a codebase. The "
    "tool is KNOWN to propose work that is ALREADY DONE because it pattern-"
    "matches on file names without checking whether the capability exists. Your "
    "ONE job: mark worth_doing=FALSE for opportunities that aren't actually "
    "worth doing given the EXACT code shown.\n\n"
    "Mark worth_doing=FALSE when ANY of these hold:\n"
    "  1. ALREADY IMPLEMENTED: the proposed capability already exists in the "
    "code shown. e.g. 'add a /history endpoint to persist reports' when a "
    "report_store + a /history route are already present. This is the most "
    "important and most common case — be aggressive about it.\n"
    "  2. DUPLICATE: it restates something the code already does under a "
    "different name.\n"
    "  3. NOT AN IMPROVEMENT: it would add complexity with no real benefit, or "
    "contradicts how the code already works.\n"
    "  4. UNGROUNDED CLAIM: the rationale references code/behavior that does NOT "
    "appear in what's shown.\n\n"
    "Mark worth_doing=TRUE only when the opportunity targets a genuine gap you "
    "can confirm is absent from the code shown. When the code shown is partial "
    "and you genuinely cannot tell, default to worth_doing=TRUE (fail-open — we "
    "would rather show a borderline opportunity than hide a real one). Emit "
    "exactly one verdict per opportunity, echoing the title verbatim."
)


def verify_opportunities(
    opportunities: List[Any],
    code_blob: str,
    provider: Any,
    deployment_hint: str = "smart",
) -> List[Any]:
    """Run the LLM critic: drop opportunities the verifier says aren't worth
    doing (already built / duplicate / not an improvement), judged against the
    SAME code that was shown to the discoverer.

    Sets `.worth_doing` + `.verify_reason` on each survivor for transparency.
    Fail-open on every axis: critic disabled, no provider, no code, empty list,
    or any exception ⇒ return the input unchanged (a noisy opportunity is
    annoying; silently hiding a real one is worse)."""
    if not opportunities or not _VERIFY_ENABLED or provider is None or not code_blob:
        return opportunities
    try:
        listing = "\n".join(
            f"{i + 1}. [{getattr(o, 'category', '')}] {getattr(o, 'title', '')}: "
            f"{(getattr(o, 'description', '') or '')[:200]} "
            f"(evidence: {'; '.join(getattr(o, 'evidence', None) or [])[:1] or ['none']})"
            for i, o in enumerate(opportunities)
        )
        user = (
            "## Source code that was analyzed\n"
            f"{code_blob[:24000]}\n\n"
            "## Candidate opportunities to verify\n"
            f"{listing}\n\n"
            "For EACH opportunity decide worth_doing. Be especially aggressive "
            "about marking FALSE anything ALREADY IMPLEMENTED in the code above. "
            "Echo each title verbatim."
        )
        report = provider.invoke_structured_sync(
            system_prompt=_VERIFY_SYSTEM,
            user_prompt=user,
            schema_class=_OppCriticReport,
            deployment_hint=deployment_hint,
        )
        refuted = {
            (v.title or "").strip().lower(): (v.reason or "")
            for v in report.verdicts
            if v.worth_doing is False
        }
        kept = []
        for o in opportunities:
            title_l = (getattr(o, "title", "") or "").strip().lower()
            if title_l in refuted:
                logger.info(
                    "opportunity critic refuted (not worth doing): %s — %s",
                    getattr(o, "title", ""), refuted[title_l],
                )
                continue
            # Annotate survivors so the UI can show the critic agreed.
            try:
                o.worth_doing = True
            except Exception:
                pass
            kept.append(o)
        return kept
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("opportunity verify pass failed (%s); keeping all", e)
        return opportunities


# ── Deterministic "already-built" prefilter ─────────────────────────────────
# The smoke run exposed the LLM critic's blind spot: it only sees the same
# ~8-file code blob the discoverer saw, so when an opportunity proposes adding a
# capability whose proof-of-existence lives in a file OUTSIDE that window (e.g.
# "add a /history endpoint" when the route is defined in analysis.py, not in the
# blob), the model can't refute it. This deterministic pass scans the FULL repo
# corpus (every key_files body + the file tree) for the routes / new files the
# opportunity proposes creating, and refutes when they already exist. Same
# philosophy as finding_critic._deterministic_prefilter — don't ask the LLM what
# code inspection can decide reliably.

# Route paths like /api/repos/{owner}/{repo}/history  or  GET /foo/bar
_ROUTE_RE = re.compile(r"(?:GET|POST|PUT|PATCH|DELETE\s+)?(/(?:api/)?[a-z][\w\-/]*(?:\{[^}]+\}[\w\-/]*)*)", re.IGNORECASE)
# "add a <name>.py" / "create <path>.ts" style new-file proposals.
_NEW_FILE_RE = re.compile(r"\b([\w./-]+\.(?:py|ts|tsx|js|jsx|go|rs))\b")
# Verbs that signal the opportunity is proposing to ADD something new (vs improve
# something that exists). Only then does "it already exists" mean "already built".
_ADD_VERBS = ("add ", "create ", "introduce ", "implement ", "build ", "new ")


def _normalize_route(route: str) -> str:
    """Collapse path params so /repos/{owner}/{repo}/history ~= /repos/{x}/{y}/history."""
    r = re.sub(r"\{[^}]+\}", "{}", route.strip().lower().rstrip("/"))
    return r


def _corpus(file_tree: List[str], key_files: Dict[str, str]) -> str:
    """Lowercased concatenation of every file body + the tree — the full search
    surface for already-built detection (NOT the truncated LLM blob)."""
    parts = list(file_tree or [])
    parts.extend((key_files or {}).values())
    return "\n".join(parts).lower()


def _proposes_adding(text: str) -> bool:
    t = (text or "").lower()
    return any(v in t for v in _ADD_VERBS)


def already_built(opp: Any, file_tree: List[str], key_files: Dict[str, str]) -> Optional[str]:
    """Return a reason string if the opportunity proposes adding something that
    ALREADY exists in the repo, else None. Conservative: only fires for clear
    'add X' proposals where X (a route or a new file) is already present."""
    title = getattr(opp, "title", "") or ""
    desc = getattr(opp, "description", "") or ""
    text = f"{title}\n{desc}"
    if not _proposes_adding(text):
        return None

    corpus = _corpus(file_tree, key_files)
    tree_lower = {p.lower() for p in (file_tree or [])}

    # 1. Proposed route already defined somewhere in the code.
    for m in _ROUTE_RE.finditer(text):
        route = _normalize_route(m.group(1))
        # Ignore trivially short/again-generic paths.
        if route.count("/") < 2 or len(route) < 6:
            continue
        if _normalize_route_present(route, corpus):
            return f"route {m.group(1)!r} already exists in the codebase"

    # 2. Proposed NEW file already exists in the tree (only when the text frames
    #    it as creating that file — 'add report_store.py').
    for m in _NEW_FILE_RE.finditer(text):
        cand = m.group(1).lower()
        base = cand.split("/")[-1]
        # Must be framed as a new file, and not just a target_file it will edit.
        if base in {p.split("/")[-1] for p in tree_lower} or any(
            p.endswith("/" + base) or p == base for p in tree_lower
        ):
            # Guard: if the SAME path is in target_files, the opp intends to EDIT
            # it (legit) — only refute when the text says add/create it.
            if re.search(rf"(?:add|create|new)\b[^.]*\b{re.escape(base)}", text.lower()):
                return f"file {base!r} already exists in the repo"

    return None


def _route_skeleton_pattern(segs: List[str]) -> str:
    """Regex matching a route's segments, `{}` params as wildcards."""
    pat_parts = []
    for s in segs:
        pat_parts.append(r"\{[^}/]+\}" if s == "{}" else re.escape(s))
    return r"/" + r"/".join(pat_parts)


def _normalize_route_present(route: str, corpus: str) -> bool:
    """Is a route equivalent to `route` present in the corpus? Params are
    wildcards. CRUCIAL: FastAPI route decorators OMIT the router's mount prefix
    (a route mounted at /api shows up as `@router.get("/repos/...")` in source),
    so a proposed `/api/repos/.../history` must also match a decorator that only
    says `/repos/.../history`. We therefore try the route as-is AND with a
    leading `api` segment stripped."""
    segs = route.strip("/").split("/")
    candidates = [segs]
    if segs and segs[0] == "api" and len(segs) > 1:
        candidates.append(segs[1:])  # prefix-stripped variant
    for cand in candidates:
        if re.search(_route_skeleton_pattern(cand), corpus):
            return True
    return False


def filter_already_built(
    opportunities: List[Any],
    file_tree: List[str],
    key_files: Dict[str, str],
) -> List[Any]:
    """Drop opportunities that propose adding something already present. Sets
    .worth_doing=False + .verify_reason on the dropped ones (for debug views)
    and returns only the survivors. Fully deterministic — runs even with no LLM."""
    kept = []
    for opp in opportunities:
        reason = already_built(opp, file_tree, key_files)
        if reason:
            logger.info("already-built prefilter refuted: %s — %s",
                        getattr(opp, "title", ""), reason)
            try:
                opp.worth_doing = False
                opp.verify_reason = f"already built: {reason}"
            except Exception:
                pass
            continue
        kept.append(opp)
    return kept


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
