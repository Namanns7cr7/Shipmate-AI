"""Tests for the OPP-* fixes that came out of the Phase-1A smoke run.

  OPP-001: token accepted from Authorization header (preferred) or legacy query.
  OPP-003: file-tree TTL cache returns cached paths without a second fetch.
  OPP-005: build_context surfaces non-404 PR-fetch errors as warnings.
"""
import asyncio

import httpx
import pytest

from app.api.routes.auth import resolve_access_token


# ── OPP-001: token resolution ────────────────────────────────────────────────

class TestTokenResolution:
    def test_prefers_bearer_header(self):
        assert resolve_access_token(authorization="Bearer abc123", access_token=None) == "abc123"

    def test_accepts_token_scheme(self):
        assert resolve_access_token(authorization="token xyz", access_token=None) == "xyz"

    def test_falls_back_to_query_param(self):
        assert resolve_access_token(authorization=None, access_token="legacy") == "legacy"

    def test_header_wins_over_query(self):
        assert resolve_access_token(authorization="Bearer hdr", access_token="qry") == "hdr"

    def test_missing_both_raises_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as ei:
            resolve_access_token(authorization=None, access_token=None)
        assert ei.value.status_code == 401

    def test_malformed_header_falls_back_to_query(self):
        # No scheme -> ignore header, use query.
        assert resolve_access_token(authorization="garbage", access_token="q") == "q"


# ── OPP-003: file-tree TTL cache ─────────────────────────────────────────────

class TestTreeCache:
    def test_cache_hit_skips_second_fetch(self, monkeypatch):
        from app.services import github_api_service as gh
        gh.clear_tree_cache()
        monkeypatch.setattr(gh, "_TREE_CACHE_TTL_S", 300)

        calls = {"n": 0}

        class _FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"tree": [{"path": "a.py", "type": "blob"},
                                             {"path": "d", "type": "tree"}]}

        class _FakeClient:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, *a, **k):
                calls["n"] += 1
                return _FakeResp()

        monkeypatch.setattr(gh.httpx, "AsyncClient", _FakeClient)

        async def run():
            first = await gh.GitHubAPIService.get_file_tree("t", "o", "r", "main")
            second = await gh.GitHubAPIService.get_file_tree("t", "o", "r", "main")
            return first, second

        first, second = asyncio.run(run())
        assert first == ["a.py"]          # only blobs
        assert second == ["a.py"]
        assert calls["n"] == 1, "second call should hit cache, not GitHub"
        gh.clear_tree_cache()

    def test_ttl_zero_disables_cache(self, monkeypatch):
        from app.services import github_api_service as gh
        gh.clear_tree_cache()
        monkeypatch.setattr(gh, "_TREE_CACHE_TTL_S", 0)

        calls = {"n": 0}

        class _FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"tree": [{"path": "x.py", "type": "blob"}]}

        class _FakeClient:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, *a, **k):
                calls["n"] += 1
                return _FakeResp()

        monkeypatch.setattr(gh.httpx, "AsyncClient", _FakeClient)

        async def run():
            await gh.GitHubAPIService.get_file_tree("t", "o", "r", "main")
            await gh.GitHubAPIService.get_file_tree("t", "o", "r", "main")

        asyncio.run(run())
        assert calls["n"] == 2, "TTL=0 must not cache"


# ── OPP-005: PR-fetch error surfaced as warning ──────────────────────────────

class TestPrFetchWarnings:
    def _patch_base(self, monkeypatch):
        from app.services import repo_analysis_service as ras
        from app.services.github_api_service import GitHubAPIService

        async def fake_repo_info(*a, **k): return {"full_name": "o/r", "owner": {"login": "o"}, "name": "r"}
        async def fake_tree(*a, **k): return ["main.py"]
        monkeypatch.setattr(GitHubAPIService, "get_repo_info", staticmethod(fake_repo_info))
        monkeypatch.setattr(GitHubAPIService, "get_file_tree", staticmethod(fake_tree))
        # No key files needed for this test.
        async def fake_fetch(cls, *a, **k): return {}
        monkeypatch.setattr(ras.RepoAnalysisService, "_fetch_files", classmethod(fake_fetch))
        return ras

    def test_500_pr_fetch_adds_warning(self, monkeypatch):
        ras = self._patch_base(monkeypatch)
        from app.services.github_api_service import GitHubAPIService

        async def boom(*a, **k):
            req = httpx.Request("GET", "https://api.github.com/x")
            resp = httpx.Response(503, request=req)
            raise httpx.HTTPStatusError("boom", request=req, response=resp)
        monkeypatch.setattr(GitHubAPIService, "get_pr_info", staticmethod(boom))

        ctx = asyncio.run(ras.RepoAnalysisService.build_context(
            token="t", owner="o", repo="r", branch="main", pr_number=7))
        assert ctx["pr_info"] is None
        assert ctx["warnings"], "a 503 PR fetch must produce a warning"
        assert "503" in ctx["warnings"][0]

    def test_404_pr_fetch_is_silent(self, monkeypatch):
        ras = self._patch_base(monkeypatch)
        from app.services.github_api_service import GitHubAPIService

        async def not_found(*a, **k):
            req = httpx.Request("GET", "https://api.github.com/x")
            resp = httpx.Response(404, request=req)
            raise httpx.HTTPStatusError("nf", request=req, response=resp)
        monkeypatch.setattr(GitHubAPIService, "get_pr_info", staticmethod(not_found))

        ctx = asyncio.run(ras.RepoAnalysisService.build_context(
            token="t", owner="o", repo="r", branch="main", pr_number=7))
        assert ctx["pr_info"] is None
        assert ctx["warnings"] == [], "a 404 PR is expected and must NOT warn"
