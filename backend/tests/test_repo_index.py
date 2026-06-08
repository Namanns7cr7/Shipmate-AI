"""Tests for the shared RepoIndex cache (Refactor #5).

Proves a repo is built once and reused within the TTL — collapsing the 2-3×
build_context + RepoLens runs per logical operation — while keying correctly on
(owner, repo, branch, include_source_corpus, pr_number) and invalidating on
demand.
"""
import asyncio

import pytest

from app.services.repo_index_service import RepoIndexService


@pytest.fixture(autouse=True)
def _clear():
    RepoIndexService.clear_cache()
    yield
    RepoIndexService.clear_cache()


def _patch_builders(monkeypatch, counter):
    """Stub RepoAnalysisService.build_context / enrich + RepoLensAgent.run so we
    can count how many times each runs."""
    from app.services import repo_index_service as ris
    from app.services.repo_analysis_service import RepoAnalysisService

    async def fake_build_context(token, owner, repo, branch="main", pr_number=None, feature_context=""):
        counter["build"] += 1
        return {"repo_info": {"owner": {"login": owner}, "name": repo},
                "file_tree": ["app/x.py"], "key_files": {}, "branch": branch}

    async def fake_enrich(token, owner, repo, ctx, **k):
        counter["enrich"] += 1
        return ctx

    monkeypatch.setattr(RepoAnalysisService, "build_context", classmethod(
        lambda cls, **kw: fake_build_context(**kw)))
    monkeypatch.setattr(RepoAnalysisService, "enrich_build_corpus", classmethod(
        lambda cls, *a, **k: fake_enrich(*a, **k)))

    # RepoLensAgent.run is sync, dispatched via to_thread inside the service.
    from app.agents import repo_lens_agent as rla

    def fake_run(self, ctx):
        counter["lens"] += 1
        return object()  # opaque, the service treats it as read-only

    monkeypatch.setattr(rla.RepoLensAgent, "run", fake_run)


def test_second_call_is_a_cache_hit(monkeypatch):
    counter = {"build": 0, "enrich": 0, "lens": 0}
    _patch_builders(monkeypatch, counter)

    async def go():
        a = await RepoIndexService.get_or_build(
            token="t", owner="o", repo="r", branch="main")
        b = await RepoIndexService.get_or_build(
            token="t", owner="o", repo="r", branch="main")
        return a, b

    a, b = asyncio.run(go())
    assert counter["build"] == 1, "build_context must run once, not per call"
    assert counter["lens"] == 1, "RepoLens must run once, not per call"
    assert a.repo_context["repo_info"]["name"] == "r"
    assert b.repo_context["repo_info"]["name"] == "r"


def test_corpus_dimension_keys_separately(monkeypatch):
    counter = {"build": 0, "enrich": 0, "lens": 0}
    _patch_builders(monkeypatch, counter)

    async def go():
        await RepoIndexService.get_or_build(
            token="t", owner="o", repo="r", branch="main", include_source_corpus=True)
        await RepoIndexService.get_or_build(
            token="t", owner="o", repo="r", branch="main", include_source_corpus=False)

    asyncio.run(go())
    # Two distinct cache keys → two builds; enrich only on the source-corpus one.
    assert counter["build"] == 2
    assert counter["enrich"] == 1


def test_branch_and_pr_dimensions_key_separately(monkeypatch):
    counter = {"build": 0, "enrich": 0, "lens": 0}
    _patch_builders(monkeypatch, counter)

    async def go():
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="dev")
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main", pr_number=7)

    asyncio.run(go())
    assert counter["build"] == 3, "branch + pr_number are part of the cache key"


def test_invalidate_forces_rebuild(monkeypatch):
    counter = {"build": 0, "enrich": 0, "lens": 0}
    _patch_builders(monkeypatch, counter)

    async def go():
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")
        RepoIndexService.invalidate("o", "r", "main")
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")

    asyncio.run(go())
    assert counter["build"] == 2, "invalidate must force a fresh build"


def test_ttl_zero_disables_cache(monkeypatch):
    counter = {"build": 0, "enrich": 0, "lens": 0}
    _patch_builders(monkeypatch, counter)
    monkeypatch.setattr("app.services.repo_index_service._TTL_S", 0)

    async def go():
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")
        await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")

    asyncio.run(go())
    assert counter["build"] == 2, "TTL=0 must rebuild every time"


def test_snapshot_isolates_mutations(monkeypatch):
    """A caller mutating the returned context must not corrupt the cached one."""
    counter = {"build": 0, "enrich": 0, "lens": 0}
    _patch_builders(monkeypatch, counter)

    async def go():
        a = await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")
        a.repo_context["mutated"] = True  # caller scribbles on its copy
        b = await RepoIndexService.get_or_build(token="t", owner="o", repo="r", branch="main")
        return b

    b = asyncio.run(go())
    assert "mutated" not in b.repo_context, "cached entry must be isolated from caller mutation"
    assert counter["build"] == 1
