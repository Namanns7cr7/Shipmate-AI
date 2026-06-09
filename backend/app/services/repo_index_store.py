"""
repo_index_store — persistent L2 for the RepoIndex (B4).

RepoIndexService caches the built repo corpus (tree + key_files + enriched
source + RepoLens output) in-memory with a TTL. That's correct for ONE process,
but the corpus is exactly what's expensive to rebuild (a recursive tree walk +
~40 file fetches + the RepoLens pass) and exactly what should survive a restart
(uvicorn --reload fires on every code change in dev; a deploy bounces the
process mid-loop). In-memory-only means every restart re-pays that cost, and two
worker processes each build their own copy.

This is the persistent layer behind the in-memory cache:
  • Keyed by (owner, repo, branch, include_source_corpus, pr_number, COMMIT_SHA).
    The SHA is the content identity — a hit means "this exact tree was already
    built", so unlike a TTL it never goes stale: a push changes the branch head
    SHA, which is a different key, which is a clean miss.
  • Stores the repo_context dict + the RepoLens output (as JSON). RepoIndexService
    rehydrates a RepoIndex from a hit and re-populates its in-memory cache, so the
    second+ request (or the post-restart request) skips the whole build.
  • Bounded: oldest rows pruned per repo.

FAIL-OPEN: every operation swallows errors (returns None / does nothing). A
persistence hiccup must degrade to "rebuild it", never break analyze.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Any, Dict, Optional

from app.services import sqlite_store

logger = logging.getLogger("shipmate.repo_index_store")

_STORE = "repo_index"
_KEEP_PER_REPO = 40       # bound history per (owner/repo)
_DEFAULT_MAX_AGE_S = int(__import__("os").getenv("REPO_INDEX_PERSIST_MAX_AGE_S", "86400"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS repo_index_cache (
    cache_key       TEXT PRIMARY KEY,   -- owner|repo|branch|src|pr|sha
    owner           TEXT NOT NULL,
    repo            TEXT NOT NULL,
    branch          TEXT NOT NULL,
    commit_sha      TEXT NOT NULL,
    repo_context_json TEXT NOT NULL,
    repo_lens_json  TEXT,
    built_at        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_repo_index_repo ON repo_index_cache(owner, repo, built_at);
"""

sqlite_store.register(
    _STORE,
    filename="shipmate_repo_index.db",
    legacy_env="SHIPMATE_REPO_INDEX_DB",
    schema=_SCHEMA,
)


def _conn() -> sqlite3.Connection:
    return sqlite_store.connect(_STORE)


def init_db() -> None:
    sqlite_store.init_schema(_STORE)


def make_key(
    owner: str, repo: str, branch: str,
    include_source_corpus: bool, pr_number: Optional[int], commit_sha: str,
) -> str:
    return f"{owner}|{repo}|{branch}|{int(bool(include_source_corpus))}|{pr_number}|{commit_sha}"


def get(
    owner: str, repo: str, branch: str,
    include_source_corpus: bool, pr_number: Optional[int], commit_sha: str,
    *, max_age_s: int = _DEFAULT_MAX_AGE_S,
) -> Optional[Dict[str, Any]]:
    """Return {'repo_context': dict, 'repo_lens': dict|None, 'built_at': int} for
    an exact (key incl. commit_sha) hit within max_age_s, else None. Because the
    key includes the SHA, max_age_s is a sanity bound (drop ancient rows), NOT a
    correctness TTL — a hit is the same content, always valid."""
    if not commit_sha:
        return None
    try:
        key = make_key(owner, repo, branch, include_source_corpus, pr_number, commit_sha)
        row = _conn().execute(
            "SELECT repo_context_json, repo_lens_json, built_at "
            "FROM repo_index_cache WHERE cache_key=?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        if max_age_s and (int(time.time()) - row["built_at"]) > max_age_s:
            return None
        return {
            "repo_context": json.loads(row["repo_context_json"]),
            "repo_lens": json.loads(row["repo_lens_json"]) if row["repo_lens_json"] else None,
            "built_at": row["built_at"],
        }
    except Exception as e:  # pragma: no cover - fail-open
        logger.debug("repo_index_store.get failed (%s)", e)
        return None


def put(
    owner: str, repo: str, branch: str,
    include_source_corpus: bool, pr_number: Optional[int], commit_sha: str,
    repo_context: Dict[str, Any], repo_lens_json: Optional[str],
) -> None:
    """Persist a built index under its commit-SHA key. `repo_lens_json` is the
    RepoLens output already serialized (the caller has the pydantic model and
    knows how to dump it); we keep storage JSON-only here. No-op on error."""
    if not commit_sha:
        return
    try:
        key = make_key(owner, repo, branch, include_source_corpus, pr_number, commit_sha)
        c = _conn()
        c.execute(
            "INSERT INTO repo_index_cache "
            "(cache_key, owner, repo, branch, commit_sha, repo_context_json, "
            " repo_lens_json, built_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(cache_key) DO UPDATE SET "
            "  repo_context_json=excluded.repo_context_json, "
            "  repo_lens_json=excluded.repo_lens_json, built_at=excluded.built_at",
            (key, owner, repo, branch, commit_sha,
             json.dumps(repo_context, default=str), repo_lens_json, int(time.time())),
        )
        c.commit()
        _prune(owner, repo)
    except Exception as e:  # pragma: no cover - fail-open
        logger.debug("repo_index_store.put failed (%s)", e)


def invalidate(owner: str, repo: str, branch: Optional[str] = None) -> int:
    """Drop persisted entries for a repo (all branches if branch is None).
    Returns rows deleted. Called alongside the in-memory invalidate after a push
    or actuate that changed the repo."""
    try:
        c = _conn()
        if branch is None:
            cur = c.execute(
                "DELETE FROM repo_index_cache WHERE owner=? AND repo=?", (owner, repo),
            )
        else:
            cur = c.execute(
                "DELETE FROM repo_index_cache WHERE owner=? AND repo=? AND branch=?",
                (owner, repo, branch),
            )
        c.commit()
        return cur.rowcount
    except Exception as e:  # pragma: no cover
        logger.debug("repo_index_store.invalidate failed (%s)", e)
        return 0


def _prune(owner: str, repo: str) -> None:
    try:
        c = _conn()
        c.execute(
            "DELETE FROM repo_index_cache WHERE owner=? AND repo=? AND cache_key NOT IN "
            "(SELECT cache_key FROM repo_index_cache WHERE owner=? AND repo=? "
            " ORDER BY built_at DESC LIMIT ?)",
            (owner, repo, owner, repo, _KEEP_PER_REPO),
        )
        c.commit()
    except Exception as e:  # pragma: no cover
        logger.debug("repo_index_store._prune failed (%s)", e)


def reset_all() -> None:
    try:
        c = _conn()
        c.execute("DELETE FROM repo_index_cache")
        c.commit()
    except Exception as e:  # pragma: no cover
        logger.debug("repo_index_store reset failed (%s)", e)


def count() -> int:
    try:
        return _conn().execute("SELECT COUNT(*) FROM repo_index_cache").fetchone()[0]
    except Exception:  # pragma: no cover
        return 0
