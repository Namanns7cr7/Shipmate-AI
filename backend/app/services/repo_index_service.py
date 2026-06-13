"""
RepoIndexService — "analyze a repo once, reuse it everywhere within a TTL".

Before this, the SAME (owner, repo, branch) got re-fetched and re-analyzed
2-3× per logical user action:
  • /build/execute called build_context + enrich_build_corpus, THEN ran
    RepoLensAgent (build.py), THEN OpportunityService.build_plan ran RepoLens
    AGAIN.
  • /analyze ran build_context + enrich + RepoLens inside the orchestrator.
  • the auto-fix loop rebuilt the context every round.
Each build_context is a recursive git-tree walk + up to ~40 file fetches +
the RepoLens pass — the heaviest part of every request.

This service is the single front door. get_or_build(...) returns a RepoIndex
(the built repo_context dict + the RepoLens output) and caches it per
(owner, repo, branch, include_source_corpus, pr_number) for a short TTL. The
second+ caller in the same operation reuses the first result instead of
re-fetching GitHub.

Design notes:
  • Sits ABOVE GitHubAPIService._tree_cache (which caches only the tree). This
    caches the whole assembled artifact: tree + key_files + enriched corpus +
    RepoLens output.
  • Cache key includes `include_source_corpus` because /analyze + /build need
    the fat (source-enriched) corpus while a lighter caller may not — two
    different artifacts for the same repo+branch.
  • Cache key includes `pr_number` so a PR-scoped analysis never collides with
    a branch-scoped one.
  • TTL default 300s, matching GitHubAPIService._tree_cache. Override with
    REPO_INDEX_TTL_S=0 to disable.
  • A returned RepoIndex hands back a COPY of the context dict so a caller that
    mutates it (the orchestrator stuffs repo_lens / warnings in) can't corrupt
    the cached entry for the next caller.
  • NEVER caches the access_token — the key is identity-only; the token is used
    transiently to build and then dropped.
  • bounded LRU-ish: capped entry count, expired entries swept on access.
  • asyncio.Lock per key so two concurrent callers for the same repo don't both
    pay the build (the second awaits the first's result).
"""
from __future__ import annotations

import asyncio
import copy
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from app.services.repo_analysis_service import RepoAnalysisService

logger = logging.getLogger("shipmate.repo_index")

_TTL_S = int(os.getenv("REPO_INDEX_TTL_S", "300"))
_MAX_ENTRIES = int(os.getenv("REPO_INDEX_MAX_ENTRIES", "64"))

_CacheKey = Tuple[str, str, str, bool, Optional[int]]


@dataclass
class RepoIndex:
    """One built+analyzed repo snapshot. `repo_context` is the dict the
    orchestrator/opportunity pipeline consume; `repo_lens` is the RepoLensOutput
    (or None if RepoLens wasn't requested / failed)."""
    repo_context: Dict[str, Any]
    repo_lens: Any = None
    built_at: float = 0.0
    source_enriched: bool = False


@dataclass
class _Entry:
    index: RepoIndex
    expires_at: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RepoIndexService:
    _cache: Dict[_CacheKey, _Entry] = {}
    # A coarse lock guarding the cache dict itself (NOT the per-key build lock).
    _dict_lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def _key(
        cls, owner: str, repo: str, branch: str,
        include_source_corpus: bool, pr_number: Optional[int],
    ) -> _CacheKey:
        return (owner, repo, branch, include_source_corpus, pr_number)

    @classmethod
    async def get_or_build(
        cls,
        *,
        token: str,
        owner: str,
        repo: str,
        branch: str = "main",
        include_source_corpus: bool = True,
        run_repo_lens: bool = True,
        pr_number: Optional[int] = None,
        feature_context: str = "",
    ) -> RepoIndex:
        """Return a cached RepoIndex for (owner, repo, branch, …) or build one.

        Returns a snapshot whose repo_context is a deep copy — safe for the
        caller to mutate. A cache miss builds: build_context → (optionally)
        enrich_build_corpus → (optionally) RepoLensAgent.run."""
        if _TTL_S <= 0:
            return await cls._build(
                token, owner, repo, branch, include_source_corpus,
                run_repo_lens, pr_number, feature_context,
            )

        key = cls._key(owner, repo, branch, include_source_corpus, pr_number)
        now = time.time()

        async with cls._dict_lock:
            cls._sweep_expired(now)
            entry = cls._cache.get(key)
            if entry is None:
                # Reserve a slot with an empty lock so concurrent callers
                # serialize on the SAME lock for this key.
                entry = _Entry(index=None, expires_at=0.0)  # type: ignore[arg-type]
                cls._cache[key] = entry

        # Per-key build lock — the first caller builds, the rest await.
        async with entry.lock:
            now = time.time()
            if entry.index is not None and entry.expires_at > now:
                logger.debug("RepoIndex HIT %s/%s@%s (src=%s pr=%s)",
                             owner, repo, branch, include_source_corpus, pr_number)
                return cls._snapshot(entry.index)

            built = await cls._build(
                token, owner, repo, branch, include_source_corpus,
                run_repo_lens, pr_number, feature_context,
            )
            entry.index = built
            entry.expires_at = time.time() + _TTL_S
            return cls._snapshot(built)

    @classmethod
    async def _build(
        cls, token, owner, repo, branch,
        include_source_corpus, run_repo_lens, pr_number, feature_context,
    ) -> RepoIndex:
        logger.debug("RepoIndex MISS — building %s/%s@%s (src=%s pr=%s)",
                     owner, repo, branch, include_source_corpus, pr_number)
        repo_context = await RepoAnalysisService.build_context(
            token=token, owner=owner, repo=repo, branch=branch,
            pr_number=pr_number, feature_context=feature_context,
        )
        if include_source_corpus:
            await RepoAnalysisService.enrich_build_corpus(
                token, owner, repo, repo_context,
            )

        repo_lens = None
        if run_repo_lens:
            try:
                from app.agents.repo_lens_agent import RepoLensAgent
                repo_lens = await asyncio.to_thread(RepoLensAgent().run, repo_context)
            except Exception as e:  # pragma: no cover - defensive, fail-open
                logger.warning("RepoIndex: RepoLens failed for %s/%s (%s); proceeding",
                               owner, repo, e)

        return RepoIndex(
            repo_context=repo_context,
            repo_lens=repo_lens,
            built_at=time.time(),
            source_enriched=include_source_corpus,
        )

    @staticmethod
    def _snapshot(index: RepoIndex) -> RepoIndex:
        """Hand back a copy so callers can freely mutate repo_context (e.g. stuff
        repo_lens/warnings in) without corrupting the cached entry. repo_lens is
        shared by reference (it's treated as read-only output)."""
        return RepoIndex(
            repo_context=copy.deepcopy(index.repo_context),
            repo_lens=index.repo_lens,
            built_at=index.built_at,
            source_enriched=index.source_enriched,
        )

    @classmethod
    def _sweep_expired(cls, now: float) -> None:
        dead = [k for k, e in cls._cache.items()
                if e.index is not None and e.expires_at <= now]
        for k in dead:
            cls._cache.pop(k, None)
        # Bound the cache: if still oversized, drop the oldest-built entries.
        if len(cls._cache) > _MAX_ENTRIES:
            ordered = sorted(
                ((k, e) for k, e in cls._cache.items() if e.index is not None),
                key=lambda kv: kv[1].index.built_at,
            )
            for k, _e in ordered[: len(cls._cache) - _MAX_ENTRIES]:
                cls._cache.pop(k, None)

    @classmethod
    def invalidate(cls, owner: str, repo: str, branch: Optional[str] = None) -> int:
        """Drop cached entries for a repo (all branches if branch is None).
        Call after a push or an actuate that changed the repo. Returns count
        dropped. Synchronous — the dict ops are atomic enough for this."""
        dropped = 0
        for k in list(cls._cache):
            if k[0] == owner and k[1] == repo and (branch is None or k[2] == branch):
                cls._cache.pop(k, None)
                dropped += 1
        return dropped

    @classmethod
    def clear_cache(cls) -> None:
        """Wipe the whole cache (tests / explicit reset)."""
        cls._cache.clear()
