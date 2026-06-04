import pytest
from app.main import _contains_dangerous_pattern


class TestContainsDangerousPatternReturnsFalseForSafeString:
    """Unit tests for _contains_dangerous_pattern with safe strings."""

    def test_plain_repo_names(self):
        """Plain repository names should not trigger dangerous pattern detection."""
        safe_repo_names = [
            "my-awesome-repo",
            "python-sdk",
            "react-components",
            "backend-api",
            "frontend-app",
            "data-pipeline",
        ]
        for repo_name in safe_repo_names:
            assert _contains_dangerous_pattern(repo_name) is False

    def test_markdown_text(self):
        """Markdown text and documentation should not trigger detection."""
        safe_markdown = [
            "# Welcome to our project",
            "## Installation\n```bash\npip install package\n```",
            "This is a **bold** statement with *italics*.",
            "- Item 1\n- Item 2\n- Item 3",
            "[Link to docs](https://example.com/docs)",
            "> This is a blockquote",
        ]
        for markdown in safe_markdown:
            assert _contains_dangerous_pattern(markdown) is False

    def test_urls(self):
        """URLs and web addresses should not trigger detection."""
        safe_urls = [
            "https://github.com/user/repo",
            "http://example.com/path?query=value",
            "https://api.github.com/repos/owner/repo",
            "ftp://files.example.com/archive.zip",
            "mailto:user@example.com",
        ]
        for url in safe_urls:
            assert _contains_dangerous_pattern(url) is False

    def test_code_comments(self):
        """Code comments and documentation should not trigger detection."""
        safe_comments = [
            "# This function calculates the sum",
            "// TODO: refactor this section",
            "/* Multi-line comment explaining logic */",
            "# Note: this is a comment about eval in general",
        ]
        for comment in safe_comments:
            assert _contains_dangerous_pattern(comment) is False

    def test_natural_language_with_keywords(self):
        """Natural language text containing keyword-like words should not trigger."""
        safe_text = [
            "Please evaluate this proposal",
            "The executive summary is below",
            "We need to compile all the data",
            "Import the necessary modules",
            "The subprocess completed successfully",
            "System operations are running smoothly",
        ]
        for text in safe_text:
            assert _contains_dangerous_pattern(text) is False

    def test_json_payloads(self):
        """JSON payloads with normal data should not trigger detection."""
        safe_json = [
            '{"name": "John", "age": 30}',
            '{"repo": "my-project", "stars": 100}',
            '{"message": "Hello world", "status": "active"}',
            '{"items": [1, 2, 3], "total": 6}',
        ]
        for json_str in safe_json:
            assert _contains_dangerous_pattern(json_str) is False

    def test_empty_and_whitespace(self):
        """Empty strings and whitespace should not trigger detection."""
        safe_empty = [
            "",
            " ",
            "\n",
            "\t",
            "   \n\t   ",
        ]
        for empty in safe_empty:
            assert _contains_dangerous_pattern(empty) is False

    def test_special_characters(self):
        """Special characters and symbols should not trigger detection."""
        safe_special = [
            "!@#$%^&*()",
            "<html><body>Content</body></html>",
            "user@example.com",
            "path/to/file.txt",
            "version-1.2.3",
        ]
        for special in safe_special:
            assert _contains_dangerous_pattern(special) is False

    def test_numeric_strings(self):
        """Numeric strings should not trigger detection."""
        safe_numeric = [
            "12345",
            "3.14159",
            "1e10",
            "+1-555-123-4567",
        ]
        for numeric in safe_numeric:
            assert _contains_dangerous_pattern(numeric) is False

    def test_mixed_case_safe_words(self):
        """Words that are safe even when they contain pattern-like substrings."""
        safe_mixed = [
            "evaluation",
            "executable",
            "compiler",
            "subprocess",
            "system",
            "import_data",
            "globals_config",
        ]
        for word in safe_mixed:
            assert _contains_dangerous_pattern(word) is False
