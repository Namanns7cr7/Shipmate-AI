"""Unit tests for JUnit-XML failure parsing in GitHubActionsService.

These cover the pure/synchronous parsing helpers that turn the CI test-gate's
uploaded junit.xml artifact into the structured failure list the CIWatcher
feeds back to the Coder agent. No network — we build the zip/XML in memory.
"""
import io
import zipfile

from app.services.github_actions_service import GitHubActionsService as G


_XML_WITH_FAILURES = b"""<?xml version="1.0"?>
<testsuites>
  <testsuite name="pytest" tests="3" failures="1" errors="1">
    <testcase classname="tests.test_x" name="test_ok" time="0.01"/>
    <testcase classname="tests.test_x" name="test_bad" time="0.01">
      <failure message="assert 422 == 200">long
traceback
here</failure>
    </testcase>
    <testcase classname="tests.test_y" name="test_broken" time="0.0">
      <error message="ImportError: cannot import name _foo">trace</error>
    </testcase>
  </testsuite>
</testsuites>"""


class TestFormatJunitFailures:
    def test_lists_only_failing_cases(self):
        out = G._format_junit_failures(_XML_WITH_FAILURES)
        assert out is not None
        assert "tests.test_x::test_bad" in out
        assert "tests.test_y::test_broken" in out
        # Passing cases must NOT appear.
        assert "test_ok" not in out

    def test_distinguishes_failure_from_error(self):
        out = G._format_junit_failures(_XML_WITH_FAILURES)
        assert "[FAILURE]" in out
        assert "[ERROR]" in out

    def test_includes_exception_message(self):
        out = G._format_junit_failures(_XML_WITH_FAILURES)
        assert "assert 422 == 200" in out
        assert "ImportError: cannot import name _foo" in out

    def test_all_passing_returns_none(self):
        xml = b'<testsuites><testsuite><testcase classname="a" name="b"/></testsuite></testsuites>'
        assert G._format_junit_failures(xml) is None

    def test_malformed_xml_returns_none(self):
        assert G._format_junit_failures(b"<not><closed>") is None

    def test_long_message_is_truncated(self):
        huge = b'<testsuites><testsuite><testcase classname="a" name="b">' \
               b'<failure message="' + (b"x" * 5000) + b'">t</failure>' \
               b'</testcase></testsuite></testsuites>'
        out = G._format_junit_failures(huge)
        assert out is not None
        assert "[truncated]" in out

    def test_failure_count_is_capped(self):
        cases = b"".join(
            b'<testcase classname="a" name="t%d"><failure message="boom">x</failure></testcase>' % i
            for i in range(60)
        )
        xml = b"<testsuites><testsuite>" + cases + b"</testsuite></testsuites>"
        out = G._format_junit_failures(xml)
        assert out is not None
        assert "list truncated" in out


class TestParseJunitZip:
    def test_extracts_junit_member(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("reports/junit.xml", _XML_WITH_FAILURES)
        out = G._parse_junit_zip(buf.getvalue())
        assert out is not None
        assert "test_bad" in out

    def test_bad_zip_returns_none(self):
        assert G._parse_junit_zip(b"not a zip file") is None

    def test_zip_without_junit_member_returns_none(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("reports/coverage.xml", b"<coverage/>")
        assert G._parse_junit_zip(buf.getvalue()) is None
