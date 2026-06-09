"""Persistent L2 for the RepoIndex, keyed by commit SHA (B4).

RepoIndexService's in-memory TTL cache dies on restart and isn't shared across
workers, so every restart re-pays the heaviest GitHub work (tree walk + ~40 file
fetches + RepoLens). repo_index_store persists the built corpus keyed by the
branch-head commit SHA — a hit means "this exact tree was already built", so it
never goes stale (a push = new SHA = clean miss) and survives restarts.
"""
import pytest

from app.services import repo_index_store as store


@pytest.fixture(autouse=True)
def _clean():
    store.reset_all()
    yield
    store.reset_all()


CTX = {
    "repo_info": {"full_name": "octo/example"},
    "file_tree": ["a.py", "b.py"],
    "key_files": {"a.py": "x = 1"},
    "branch": "main",
}


class TestRoundTrip:
    def test_put_then_get_same_sha_hits(self):
        store.put("octo", "example", "main", True, None, "sha123", CTX, None)
        hit = store.get("octo", "example", "main", True, None, "sha123")
        assert hit is not None
        assert hit["repo_context"]["file_tree"] == ["a.py", "b.py"]

    def test_different_sha_is_miss(self):
        store.put("octo", "example", "main", True, None, "sha123", CTX, None)
        # A push changes the SHA → different key → clean miss (no stale serve).
        assert store.get("octo", "example", "main", True, None, "shaXYZ") is None

    def test_repo_lens_json_round_trips(self):
        lens = '{"primary_language": "Python", "tech_stack": ["FastAPI"]}'
        store.put("octo", "example", "main", True, None, "sha1", CTX, lens)
        hit = store.get("octo", "example", "main", True, None, "sha1")
        assert hit["repo_lens"]["primary_language"] == "Python"

    def test_include_source_corpus_is_part_of_key(self):
        store.put("octo", "example", "main", True, None, "sha1", CTX, None)
        # Same SHA but the light (no-source) variant is a different artifact.
        assert store.get("octo", "example", "main", False, None, "sha1") is None

    def test_pr_number_is_part_of_key(self):
        store.put("octo", "example", "main", True, 7, "sha1", CTX, None)
        assert store.get("octo", "example", "main", True, None, "sha1") is None
        assert store.get("octo", "example", "main", True, 7, "sha1") is not None


class TestSanityBoundAndInvalidate:
    def test_max_age_drops_ancient_rows(self):
        store.put("octo", "example", "main", True, None, "sha1", CTX, None)
        # Sleep comfortably past a 1s bound (int-second truncation makes a 1.1s
        # delta ambiguous; 2.1s is unambiguously > 1).
        import time
        time.sleep(2.1)
        assert store.get("octo", "example", "main", True, None, "sha1", max_age_s=1) is None
        # A generous bound still hits.
        assert store.get("octo", "example", "main", True, None, "sha1", max_age_s=86400) is not None

    def test_invalidate_branch(self):
        store.put("octo", "example", "main", True, None, "sha1", CTX, None)
        store.put("octo", "example", "dev", True, None, "sha2", CTX, None)
        dropped = store.invalidate("octo", "example", "main")
        assert dropped == 1
        assert store.get("octo", "example", "main", True, None, "sha1") is None
        assert store.get("octo", "example", "dev", True, None, "sha2") is not None

    def test_invalidate_all_branches(self):
        store.put("octo", "example", "main", True, None, "sha1", CTX, None)
        store.put("octo", "example", "dev", True, None, "sha2", CTX, None)
        store.invalidate("octo", "example", None)
        assert store.count() == 0

    def test_no_sha_is_noop(self):
        store.put("octo", "example", "main", True, None, "", CTX, None)
        assert store.count() == 0
        assert store.get("octo", "example", "main", True, None, "") is None
