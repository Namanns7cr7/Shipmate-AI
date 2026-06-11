"""Shared pytest fixtures.

The RepoIndexService keeps an in-process TTL cache of built repo contexts
(Refactor #5). Across tests that all use synthetic owners/repos like "o/r@main",
one test's cached entry would otherwise satisfy another test's request — e.g. a
test that patches build_context to raise (expecting a 502) gets a stale cache
HIT and the patched function is never called. Clear the cache before every test
so the in-process cache can't leak state between tests.
"""
import pytest


@pytest.fixture(autouse=True)
def _clear_repo_index_cache():
    try:
        from app.services.repo_index_service import RepoIndexService
        RepoIndexService.clear_cache()
    except Exception:
        pass
    yield
    try:
        from app.services.repo_index_service import RepoIndexService
        RepoIndexService.clear_cache()
    except Exception:
        pass
