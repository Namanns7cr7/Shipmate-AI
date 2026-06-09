"""Semantic finding dedup (B1).

The bug: exact-signature dedup (kind::title::file) let GuardRail re-word the
SAME finding every run, minting a fresh signature each time and defeating the
journal. finding_memory remembers a shipped/dismissed finding's TEXT as a
vector and suppresses future REPHRASES by cosine similarity — so wording no
longer matters.

These tests use the lexical default embedder (no network), which is exactly the
mechanism that catches a rephrase: the same issue described two ways shares its
content words.
"""
import pytest

from app.services import finding_memory as fm


@pytest.fixture(autouse=True)
def _clean_memory():
    fm.set_embedder(None)  # ensure lexical default
    fm.reset_all()
    yield
    fm.reset_all()
    fm.set_embedder(None)


class _Finding:
    """Minimal finding-shaped object (title + description)."""
    def __init__(self, title, description=""):
        self.title = title
        self.description = description


REPO = "octo/example"


class TestRememberAndNearest:
    def test_identical_text_scores_high(self):
        fm.remember(REPO, "guardrail::a::f", "guardrail", "shipped",
                    "Access token leaked in query parameter",
                    "The token is passed as a URL query param and ends up in logs.")
        sim, row = fm.nearest(
            REPO, "Access token leaked in query parameter",
            "The token is passed as a URL query param and ends up in logs.",
        )
        assert row is not None
        assert sim > 0.95

    def test_rephrase_scores_above_threshold(self):
        # Shipped finding, original wording.
        fm.remember(REPO, "guardrail::orig::f", "guardrail", "shipped",
                    "Access token leaked in query parameter",
                    "The GitHub access token is accepted as a URL query parameter "
                    "and is exposed in server logs and Referer headers.")
        # A genuine REPHRASE of the same issue (different words, same meaning).
        sim, row = fm.nearest(
            REPO, "Token exposed via URL query string",
            "The access token is read from a query parameter, leaking it into "
            "request logs and the Referer header.",
        )
        assert row is not None
        # Shares 'token', 'query', 'parameter', 'logs', 'referer', 'access',
        # 'exposed/leak' — comfortably over the 0.82 threshold.
        assert sim >= fm._SIM_THRESHOLD, f"rephrase only scored {sim:.3f}"

    def test_unrelated_finding_scores_low(self):
        fm.remember(REPO, "guardrail::orig::f", "guardrail", "shipped",
                    "Access token leaked in query parameter",
                    "Token is in the URL query param and leaks into logs.")
        sim, _ = fm.nearest(
            REPO, "Add pagination to the repository list endpoint",
            "The /repos endpoint returns all repos at once with no page cursor.",
        )
        assert sim < fm._SIM_THRESHOLD


class TestSuppression:
    def test_rephrase_is_suppressed(self):
        fm.remember(REPO, "guardrail::orig::f", "guardrail", "shipped",
                    "Wildcard CORS allows any origin",
                    "CORS is configured with allow_origins=['*'] permitting any "
                    "domain to make credentialed requests.")
        assert fm.is_semantically_suppressed(
            REPO, "Permissive CORS configuration accepts all origins",
            "The CORS policy uses a wildcard origin so any domain can send "
            "credentialed cross-origin requests.",
        ) is True

    def test_fresh_finding_not_suppressed(self):
        fm.remember(REPO, "guardrail::orig::f", "guardrail", "shipped",
                    "Wildcard CORS allows any origin", "allow_origins=['*']")
        assert fm.is_semantically_suppressed(
            REPO, "Missing rate limiting on the analyze endpoint",
            "POST /api/analyze has no per-IP throttle and can be abused.",
        ) is False

    def test_empty_memory_suppresses_nothing(self):
        assert fm.is_semantically_suppressed(REPO, "anything", "at all") is False

    def test_filter_drops_only_rephrases(self):
        fm.remember(REPO, "guardrail::orig::f", "guardrail", "dismissed",
                    "OAuth state stored in memory lost on restart",
                    "The OAuth CSRF state is kept in a process dict and lost when "
                    "the server restarts, weakening CSRF protection.")
        findings = [
            _Finding("In-memory OAuth state is wiped on server restart",
                     "OAuth state lives in a memory dict and disappears on "
                     "restart, weakening CSRF protection."),   # rephrase → drop
            _Finding("Add a /health readiness endpoint",
                     "There is no health endpoint for the load balancer."),  # keep
        ]
        kept = fm.filter_semantic_duplicates(findings, REPO)
        titles = [f.title for f in kept]
        assert "Add a /health readiness endpoint" in titles
        assert all("OAuth" not in t for t in titles)


class TestRepoIsolationAndFailOpen:
    def test_memory_is_per_repo(self):
        fm.remember("a/one", "guardrail::x::f", "guardrail", "shipped",
                    "Wildcard CORS allows any origin", "allow_origins=['*']")
        # Same text, DIFFERENT repo → not suppressed.
        assert fm.is_semantically_suppressed(
            "b/two", "Wildcard CORS allows any origin", "allow_origins=['*']",
        ) is False

    def test_only_terminal_states_suppress(self):
        # in_progress is NOT a suppressing state — a finding mid-flight shouldn't
        # silently hide a fresh, genuinely-different proposal.
        fm.remember(REPO, "guardrail::x::f", "guardrail", "in_progress",
                    "Wildcard CORS allows any origin", "allow_origins=['*']")
        assert fm.is_semantically_suppressed(
            REPO, "CORS wildcard permits all origins",
            "allow_origins set to '*' lets any domain in.",
        ) is False

    def test_filter_no_repo_returns_input(self):
        findings = [_Finding("x"), _Finding("y")]
        assert fm.filter_semantic_duplicates(findings, "") == findings


class TestPluggableEmbedder:
    def test_custom_embedder_used_and_space_isolated(self):
        # A trivial custom embedder tagged 'fake'. Remembered + query use it.
        def fake(text):
            # one-hot on the first content token — identical first token ⇒ sim 1.
            toks = [t for t in text.lower().split() if len(t) > 2]
            return "fake", ({toks[0]: 1.0} if toks else {})

        fm.set_embedder(fake)
        fm.remember(REPO, "g::x::f", "guardrail", "shipped", "cors wildcard", "")
        # Same leading token under the SAME embedder space → suppressed.
        assert fm.is_semantically_suppressed(REPO, "cors misconfig", "") is True
        # Switching back to lexical changes vec_kind; the 'fake'-tagged row is
        # skipped (never compare across spaces) → not suppressed.
        fm.set_embedder(None)
        assert fm.is_semantically_suppressed(REPO, "cors wildcard", "") is False
