r"""
diff_apply — apply a unified diff to a source string, stdlib-only.

Tier-2 "diff mode" lets the Coder emit a unified diff instead of a full file
rewrite. For large files this is a big token saving and — bonus — it makes
the scope_guard's job easier (a diff that doesn't touch a region can't drop
it). We deliberately avoid the `unidiff` PyPI package so there's no new
dependency / version-set merge: this is a focused hunk applier built on the
standard unified-diff format.

Contract (see `apply_unified_diff`):
  • Returns the patched string on success.
  • Returns None on ANY uncertainty — malformed diff, context mismatch,
    hunk that doesn't locate, or (for .py targets) a result that no longer
    parses. None is the caller's signal to fall back to a full-file rewrite.
    We bias hard toward None: a wrong silent apply is far worse than a
    fallback.

Supported:
  • Standard @@ -l,s +l,s @@ hunk headers (the line numbers are treated as
    HINTS — we relocate each hunk by matching its context/removed lines, so
    minor line drift between the diff's base and the actual file is tolerated).
  • Multiple hunks per file.
  • Leading ' ' (context), '-' (remove), '+' (add) line prefixes.
  • Optional ---/+++ file header lines (ignored — single-file applier).
  • '\ No newline at end of file' markers (ignored).

Not supported (returns None): git binary patches, rename/mode headers with
no body, fuzzy matching beyond exact context relocation.
"""
from __future__ import annotations

import ast
import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger("shipmate.diff_apply")

_HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


class _Hunk:
    __slots__ = ("old_start", "old_count", "lines")

    def __init__(self, old_start: int, old_count: int, lines: List[str]) -> None:
        self.old_start = old_start          # 1-based, from header (a hint)
        self.old_count = old_count
        self.lines = lines                  # raw body lines incl. prefix char

    def old_block(self) -> List[str]:
        """The lines this hunk expects to find (context + removed)."""
        out: List[str] = []
        for ln in self.lines:
            if ln and ln[0] in (" ", "-"):
                out.append(ln[1:])
        return out

    def new_block(self) -> List[str]:
        """The lines this hunk produces (context + added)."""
        out: List[str] = []
        for ln in self.lines:
            if not ln:
                # A truly empty body line == an empty context line.
                out.append("")
                continue
            if ln[0] in (" ", "+"):
                out.append(ln[1:])
        return out


def _parse_hunks(diff_text: str) -> Optional[List[_Hunk]]:
    """Parse a unified diff into hunks. None if no valid hunk header is found
    or a header is malformed."""
    lines = diff_text.splitlines()
    hunks: List[_Hunk] = []
    i = 0
    n = len(lines)
    # Skip any leading file headers / preamble until the first @@.
    while i < n and not lines[i].startswith("@@"):
        i += 1
    if i >= n:
        return None  # no hunk header at all
    while i < n:
        m = _HUNK_HEADER_RE.match(lines[i])
        if not m:
            # Non-hunk line between hunks (e.g. stray ---/+++): skip it.
            if lines[i].startswith("@@"):
                return None  # looked like a header but didn't parse
            i += 1
            continue
        old_start = int(m.group(1))
        old_count = int(m.group(2)) if m.group(2) is not None else 1
        i += 1
        body: List[str] = []
        while i < n and not lines[i].startswith("@@"):
            ln = lines[i]
            if ln.startswith("\\"):       # "\ No newline at end of file"
                i += 1
                continue
            # Valid body lines start with ' ', '-', '+'. A bare empty string
            # is an empty context line. Anything else ends the hunk body
            # (e.g. a new file header following without a @@).
            if ln == "" or (ln and ln[0] in (" ", "-", "+")):
                body.append(ln)
                i += 1
            else:
                break
        hunks.append(_Hunk(old_start, old_count, body))
    return hunks or None


def _locate(haystack: List[str], needle: List[str], hint: int) -> Optional[int]:
    """Find `needle` as a contiguous slice of `haystack`, preferring the
    position closest to `hint` (0-based). None if not found exactly once-
    enough to be safe. Empty needle (pure insertion) anchors at the hint."""
    if not needle:
        return max(0, min(hint, len(haystack)))
    matches: List[int] = []
    last = len(haystack) - len(needle)
    for start in range(0, last + 1):
        if haystack[start:start + len(needle)] == needle:
            matches.append(start)
    if not matches:
        return None
    # Closest to the header hint (handles a file with repeated blocks).
    return min(matches, key=lambda s: abs(s - hint))


def apply_unified_diff(original: str, diff_text: str) -> Optional[str]:
    """Apply `diff_text` to `original`. Returns the patched string, or None
    on any failure (caller should fall back to a full-file rewrite).

    Diffs don't apply to a non-existent file — for a brand-new file pass the
    full content via the normal (full) path, not here. We return None when
    `original` is empty and the diff has context to match."""
    hunks = _parse_hunks(diff_text)
    if not hunks:
        return None

    src = original.splitlines()
    # Apply hunks in order, tracking the running offset so later hunks'
    # hints account for earlier insertions/deletions.
    result = list(src)
    offset = 0
    for h in hunks:
        old = h.old_block()
        new = h.new_block()
        hint = (h.old_start - 1) + offset      # header is 1-based
        pos = _locate(result, old, hint)
        if pos is None:
            logger.info("diff_apply: hunk context not found (start=%d)", h.old_start)
            return None
        result[pos:pos + len(old)] = new
        offset += len(new) - len(old)

    patched = "\n".join(result)
    # Preserve a trailing newline if the original had one (splitlines drops it).
    if original.endswith("\n") and not patched.endswith("\n"):
        patched += "\n"

    return patched


def apply_and_validate(
    original: str, diff_text: str, path: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Apply a diff and, for .py targets, verify the result still parses.

    Returns (patched_or_None, error_or_None):
      • (str, None)  — applied cleanly (and parses, if .py)
      • (None, reason) — failed to apply, or applied but broke .py syntax
        (when the ORIGINAL parsed — a diff shouldn't introduce a syntax
        error into previously-valid code).
    """
    patched = apply_unified_diff(original, diff_text)
    if patched is None:
        return None, "diff did not apply (context mismatch or malformed)"

    if path.endswith(".py"):
        try:
            ast.parse(patched)
        except SyntaxError as e:
            # Only treat as failure if the original was itself valid — we
            # don't want to block a diff that's fixing a pre-existing break.
            try:
                ast.parse(original)
                original_ok = True
            except SyntaxError:
                original_ok = False
            if original_ok:
                return None, f"patched .py no longer parses: {e}"
    return patched, None
