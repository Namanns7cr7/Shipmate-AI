"""
Finding-journal API — read/write the persisted state of each finding.

GET  /api/findings/journal?repo=owner/name   — list journal rows for a repo
POST /api/findings/dismiss                    — mark a finding dismissed
POST /api/findings/reopen                     — clear a dismissal (back to fresh)
POST /api/findings/signature                  — compute the canonical signature
                                                 for a finding (so the frontend
                                                 keys match the backend exactly)

The journal is the shared source of truth between the CLI loop, the UI's
"Apply Fix" button, and the autonomous loop. States:
  in_progress — a patch/PR is in flight
  shipped     — a PR was opened (and, ideally, CI went green)
  dismissed   — user (or the loop) decided not to pursue it
  parked      — the loop gave up after repeated failed attempts

Signatures use the SAME `kind::title::file` scheme as
coder_orchestrator._finding_signature and coder_loop._finding_signature so a
finding actuated from any surface maps to one journal row. We re-implement the
formula here (rather than import from the orchestrator) to keep this route
dependency-light, and we cover the parity with a test.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import inflight_registry as ir

router = APIRouter(tags=["findings"])
logger = logging.getLogger("shipmate.findings_route")


def finding_signature(kind: str, title: str, file: Optional[str]) -> str:
    """Canonical `kind::title::file` signature. MUST stay in lockstep with
    coder_orchestrator._finding_signature / coder_loop._finding_signature."""
    t = (title or "").strip().lower()[:80]
    f = (file or "").lower()
    return f"{kind}::{t}::{f}"


class FindingRef(BaseModel):
    """The minimal finding identity the UI sends to mutate journal state."""
    kind: str
    title: str
    file: Optional[str] = None
    repo_full_name: str
    pr_url: Optional[str] = None
    notes: Optional[str] = None


class SignatureRequest(BaseModel):
    kind: str
    title: str
    file: Optional[str] = None


@router.get("/findings/journal")
async def get_journal(
    repo: str = Query(..., description="owner/name"),
    state: Optional[str] = Query(None, description="filter: in_progress|shipped|dismissed|parked"),
) -> Dict[str, Any]:
    """Return all journal rows for a repo, plus a sig->state map the UI can
    join against its rendered findings in O(1)."""
    state_in = [state] if state else None
    rows: List[Dict[str, Any]] = ir.journal_list(repo_full_name=repo, state_in=state_in)
    sig_state = {r["finding_sig"]: r["state"] for r in rows}
    return {"repo": repo, "rows": rows, "state_map": sig_state}


@router.post("/findings/signature")
async def compute_signature(req: SignatureRequest) -> Dict[str, str]:
    """Compute the canonical signature for a finding. The frontend calls this
    (or replicates the formula) so its journal lookups key correctly."""
    return {"signature": finding_signature(req.kind, req.title, req.file)}


@router.post("/findings/dismiss")
async def dismiss_finding(ref: FindingRef) -> Dict[str, Any]:
    """Mark a finding dismissed so it's hidden by default and skipped by the
    autonomous loop."""
    sig = finding_signature(ref.kind, ref.title, ref.file)
    try:
        ir.journal_set_state(
            sig, ref.repo_full_name, "dismissed",
            notes=ref.notes or "dismissed via UI",
        )
    except Exception as e:
        logger.warning("dismiss_finding failed: %s", e)
        raise HTTPException(status_code=500, detail=f"could not dismiss: {e}")
    return {"signature": sig, "state": "dismissed"}


@router.post("/findings/reopen")
async def reopen_finding(ref: FindingRef) -> Dict[str, Any]:
    """Reverse a dismissal/park by deleting the journal row, so the finding
    reappears as fresh on the next analyze. (We delete rather than set a
    'fresh' state because absence-from-journal IS the fresh state everywhere
    else in the system.)"""
    sig = finding_signature(ref.kind, ref.title, ref.file)
    existing = ir.journal_get_state(sig)
    if existing is None:
        return {"signature": sig, "state": "fresh", "note": "was not in journal"}
    if existing.get("state") not in ("dismissed", "parked"):
        raise HTTPException(
            status_code=409,
            detail=f"can only reopen dismissed/parked findings; this is '{existing.get('state')}'",
        )
    ir.journal_delete(sig)
    return {"signature": sig, "state": "fresh"}
