"""Unit tests for ScopeGuard — the drift detector that catches whole-file
rewrites silently dropping untested infrastructure.

The two anchor cases (test_drops_lifespan_hook, test_gitignore_line_deletion)
are the real misses that motivated this guard: patches that passed the
pytest gate while deleting untested code/config.
"""
from app.services import scope_guard as sg


# ── .py top-level symbol drops ──────────────────────────────────────────────

class TestPySymbolDrop:
    def test_drops_lifespan_hook(self):
        """The real miss: a main.py rewrite that drops _lifespan + _BodyReplayRequest."""
        original = (
            "import os\n"
            "def _validate_origin(o): return o\n"
            "async def _lifespan(app):\n"
            "    yield\n"
            "class _BodyReplayRequest:\n"
            "    pass\n"
            "app = FastAPI(lifespan=_lifespan)\n"
        )
        new = (
            "import os\n"
            "def _validate_origin(o): return o\n"
            "app = FastAPI()\n"
        )
        issues = sg.check_file("backend/app/main.py", original, new,
                               rationale="add JSON body sanitization")
        assert issues, "should flag the dropped _lifespan / _BodyReplayRequest"
        assert "_lifespan" in issues[0]
        assert "_BodyReplayRequest" in issues[0]

    def test_no_drop_is_clean(self):
        original = "def a(): pass\ndef b(): pass\n"
        new = "def a(): pass\ndef b(): pass\ndef c(): pass\n"  # added, dropped none
        assert sg.check_file("x.py", original, new) == []

    def test_removal_intent_relaxes_check(self):
        """A declared cleanup/refactor legitimately deletes defs — don't block."""
        original = "def keep(): pass\ndef _dupe(): pass\n"
        new = "def keep(): pass\n"
        # No relaxation -> flagged
        assert sg.check_file("x.py", original, new) != []
        # With removal intent in rationale -> clean
        assert sg.check_file("x.py", original, new,
                             rationale="remove the duplicate _dupe definition") == []
        # Intent in summary also relaxes
        assert sg.check_file("x.py", original, new, summary="consolidate duplicates") == []

    def test_new_file_is_clean(self):
        """A brand-new file (empty original) can't drop anything."""
        assert sg.check_file("new.py", "", "def f(): pass\n") == []

    def test_unparseable_new_content_defers(self):
        """Broken new content is ast_lint/smoke's job, not the scope guard's."""
        original = "def a(): pass\n"
        new = "def a(: pass\n"  # syntax error
        assert sg.check_file("x.py", original, new) == []

    def test_class_and_assignment_drops_flagged(self):
        original = "API_KEY = 1\nclass Foo: pass\ndef bar(): pass\n"
        new = "def bar(): pass\n"
        issues = sg.check_file("x.py", original, new)
        assert issues
        assert "API_KEY" in issues[0] and "Foo" in issues[0]

    def test_annotated_assignment_drop_flagged(self):
        original = "ALLOWED: list = []\ndef f(): pass\n"
        new = "def f(): pass\n"
        issues = sg.check_file("x.py", original, new)
        assert issues and "ALLOWED" in issues[0]

    def test_dunder_all_drop_ignored(self):
        original = "__all__ = ['a']\ndef a(): pass\n"
        new = "def a(): pass\n"
        assert sg.check_file("x.py", original, new) == []


# ── protected non-.py line drops ────────────────────────────────────────────

class TestProtectedFileLineDrop:
    def test_gitignore_line_deletion(self):
        """The real miss: a .gitignore patch that deletes reports/ + junit.xml."""
        original = (
            "__pycache__/\n"
            "*.pyc\n"
            "reports/\n"
            "junit.xml\n"
            "dist/\n"
        )
        new = (
            "__pycache__/\n"
            "*.pyc\n"
        )
        issues = sg.check_file(".gitignore", original, new,
                               rationale="add bytecode entry to gitignore")
        assert issues, "should flag the removed reports/ junit.xml dist/ lines"
        assert "reports/" in issues[0] or "junit.xml" in issues[0]

    def test_gitignore_append_is_clean(self):
        original = "__pycache__/\n*.pyc\n"
        new = "__pycache__/\n*.pyc\nreports/\njunit.xml\n"  # only added
        assert sg.check_file(".gitignore", original, new) == []

    def test_requirements_drop_flagged(self):
        original = "fastapi==0.104.1\nhttpx>=0.23.0\npydantic>=2.0.0\n"
        new = "fastapi==0.104.1\npydantic>=2.0.0\n"  # dropped httpx
        issues = sg.check_file("backend/requirements.txt", original, new)
        assert issues and "httpx" in issues[0]

    def test_workflow_yaml_line_drop_flagged(self):
        original = "jobs:\n  test:\n    runs-on: ubuntu\n  lint:\n    runs-on: ubuntu\n"
        new = "jobs:\n  test:\n    runs-on: ubuntu\n"  # dropped the lint job lines
        issues = sg.check_file(".github/workflows/ci.yml", original, new)
        assert issues

    def test_comment_only_removal_is_clean(self):
        """Removing comments/blank lines isn't drift."""
        original = "# a comment\nreports/\n\n# another\njunit.xml\n"
        new = "reports/\njunit.xml\n"
        assert sg.check_file(".gitignore", original, new) == []

    def test_removal_intent_relaxes_protected(self):
        original = "reports/\njunit.xml\nstale-entry/\n"
        new = "reports/\njunit.xml\n"
        assert sg.check_file(".gitignore", original, new,
                             rationale="remove the stale-entry line") == []

    def test_non_protected_file_not_checked(self):
        """A regular .md / .json file isn't line-diffed."""
        original = "line a\nline b\nline c\n"
        new = "line a\n"
        assert sg.check_file("README.md", original, new) == []


# ── whole-patch API ─────────────────────────────────────────────────────────

class TestCheckPatch:
    def test_aggregates_across_files(self):
        files = [
            {"path": "x.py", "new_content": "def a(): pass\n", "rationale": "tweak"},
            {"path": ".gitignore", "new_content": "*.pyc\n", "rationale": "tidy"},
        ]
        originals = {
            "x.py": "def a(): pass\ndef b(): pass\n",
            ".gitignore": "*.pyc\nreports/\n",
        }
        issues = sg.check_patch(files, originals, summary="small fixes")
        # Both a dropped def (b) and a dropped gitignore line (reports/)
        assert len(issues) == 2

    def test_clean_patch_returns_empty(self):
        files = [{"path": "x.py", "new_content": "def a(): pass\ndef b(): pass\ndef c(): pass\n"}]
        originals = {"x.py": "def a(): pass\ndef b(): pass\n"}
        assert sg.check_patch(files, originals) == []
