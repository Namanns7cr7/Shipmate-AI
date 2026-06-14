"""Shared pytest fixtures.

The RepoIndexService keeps an in-process TTL cache of built repo contexts
(Refactor #5). Across tests that all use synthetic owners/repos like "o/r@main",
one test's cached entry would otherwise satisfy another test's request — e.g. a
test that patches build_context to raise (expecting a 502) gets a stale cache
HIT and the patched function is never called. Clear the cache before every test
so the in-process cache can't leak state between tests.

The memory/observability stores added with the architecture work persist to
sqlite under the default store dir (/tmp). Analyze/actuate integration tests
WRITE to them (finding_memory.remember on a shipped/dismissed finding,
capability_store snapshots on a GuardRail pass), which could leak into a later
recurrence/golden test as a spurious semantic suppression or false drift. Reset
them around every test too, alongside the in-memory cache.
"""
import pytest


def _reset_memory_stores():
    for mod in ("finding_memory", "capability_store", "coder_lessons",
                "run_trace", "repo_index_store"):
        try:
            m = __import__(f"app.services.{mod}", fromlist=["reset_all"])
            m.reset_all()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def _clear_repo_index_cache():
    try:
        from app.services.repo_index_service import RepoIndexService
        RepoIndexService.clear_cache()
    except Exception:
        pass
    _reset_memory_stores()
    yield
    try:
        from app.services.repo_index_service import RepoIndexService
        RepoIndexService.clear_cache()
    except Exception:
        pass
    _reset_memory_stores()
