"""Unit tests for diff_apply — the stdlib unified-diff applier behind
Tier-2 diff mode. The key behaviours: clean apply, context relocation
under line drift, and None-on-any-uncertainty so the caller can fall back
to a full-file rewrite.
"""
from app.services import diff_apply as da


_ORIGINAL = """\
def alpha():
    return 1


def beta():
    return 2


def gamma():
    return 3
"""


class TestApplyUnifiedDiff:
    def test_simple_single_hunk(self):
        diff = (
            "@@ -5,2 +5,2 @@\n"
            " def beta():\n"
            "-    return 2\n"
            "+    return 22\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None
        assert "return 22" in out
        assert "return 1" in out and "return 3" in out  # untouched
        assert out.endswith("\n")

    def test_pure_insertion(self):
        diff = (
            "@@ -2,1 +2,2 @@\n"
            "     return 1\n"
            "+    # added comment\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None
        assert "# added comment" in out

    def test_deletion(self):
        diff = (
            "@@ -9,3 +9,1 @@\n"
            " def gamma():\n"
            "-    return 3\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None
        assert "return 3" not in out
        assert "def gamma" in out

    def test_multiple_hunks(self):
        diff = (
            "@@ -1,2 +1,2 @@\n"
            " def alpha():\n"
            "-    return 1\n"
            "+    return 11\n"
            "@@ -9,2 +9,2 @@\n"
            " def gamma():\n"
            "-    return 3\n"
            "+    return 33\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None
        assert "return 11" in out and "return 33" in out
        assert "return 2" in out  # middle untouched

    def test_context_relocation_under_line_drift(self):
        """Header line numbers are stale, but context still matches —
        the applier should relocate the hunk, not fail."""
        diff = (
            "@@ -999,2 +999,2 @@\n"   # bogus line numbers
            " def beta():\n"
            "-    return 2\n"
            "+    return 222\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None
        assert "return 222" in out

    def test_context_mismatch_returns_none(self):
        diff = (
            "@@ -5,2 +5,2 @@\n"
            " def NONEXISTENT():\n"
            "-    return 999\n"
            "+    return 1000\n"
        )
        assert da.apply_unified_diff(_ORIGINAL, diff) is None

    def test_no_hunk_header_returns_none(self):
        assert da.apply_unified_diff(_ORIGINAL, "just some text\nno diff here\n") is None

    def test_empty_diff_returns_none(self):
        assert da.apply_unified_diff(_ORIGINAL, "") is None

    def test_ignores_file_headers(self):
        diff = (
            "--- a/x.py\n"
            "+++ b/x.py\n"
            "@@ -5,2 +5,2 @@\n"
            " def beta():\n"
            "-    return 2\n"
            "+    return 2222\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None and "return 2222" in out

    def test_no_newline_marker_ignored(self):
        diff = (
            "@@ -5,2 +5,2 @@\n"
            " def beta():\n"
            "-    return 2\n"
            "+    return 2\n"
            "\\ No newline at end of file\n"
        )
        out = da.apply_unified_diff(_ORIGINAL, diff)
        assert out is not None


class TestApplyAndValidate:
    def test_valid_python_result(self):
        diff = (
            "@@ -5,2 +5,2 @@\n"
            " def beta():\n"
            "-    return 2\n"
            "+    return 22\n"
        )
        out, err = da.apply_and_validate(_ORIGINAL, diff, "x.py")
        assert err is None
        assert out is not None and "return 22" in out

    def test_diff_that_breaks_python_syntax_returns_none(self):
        """A diff that turns valid .py into invalid .py must be rejected
        (so the caller falls back to a full rewrite)."""
        diff = (
            "@@ -1,2 +1,2 @@\n"
            " def alpha():\n"
            "-    return 1\n"
            "+    return 1 +\n"      # trailing operator -> syntax error
        )
        out, err = da.apply_and_validate(_ORIGINAL, diff, "x.py")
        assert out is None
        assert err is not None and "parse" in err.lower()

    def test_non_py_skips_syntax_check(self):
        original = "line one\nline two\nline three\n"
        diff = (
            "@@ -2,1 +2,1 @@\n"
            "-line two\n"
            "+line 2 changed (this would be invalid python but it's a txt)\n"
        )
        out, err = da.apply_and_validate(original, diff, "notes.txt")
        assert err is None and out is not None

    def test_failed_apply_reports_error(self):
        out, err = da.apply_and_validate(_ORIGINAL, "garbage", "x.py")
        assert out is None and err is not None
