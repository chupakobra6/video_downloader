"""Tests for utilities."""

import tempfile
from pathlib import Path

from src.utils import read_links_file, validate_urls


def test_read_links_file_comprehensive() -> None:
    """Test comprehensive links file reading functionality."""
    # Test existing file with URLs and comments
    content = """
# Comment
https://example.com/video1
https://example.com/video2

# Another comment
https://example.com/video3
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        f.flush()

        try:
            links = read_links_file(Path(f.name))
            expected = [
                "https://example.com/video1",
                "https://example.com/video2",
                "https://example.com/video3",
            ]
            assert links == expected
        finally:
            Path(f.name).unlink()

    # Test non-existent file (creates template)
    with tempfile.TemporaryDirectory() as tmpdir:
        links_path = Path(tmpdir) / "nonexistent.txt"
        links = read_links_file(links_path)
        assert links == []
        assert links_path.exists()
        content = links_path.read_text(encoding="utf-8")
        assert "# Add your URLs here, one per line" in content

    # Test empty file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        f.flush()
        try:
            links = read_links_file(Path(f.name))
            assert links == []
        finally:
            Path(f.name).unlink()


def test_validate_urls_valid() -> None:
    """Test validation of valid URLs."""
    valid_urls = validate_urls(
        [
            "https://example.com/video1",
            "http://example.com/video2",
            "https://youtube.com/watch?v=123",
        ]
    )
    assert len(valid_urls) == 3


def test_validate_urls_invalid() -> None:
    """Test validation of invalid URLs."""
    mixed_urls = validate_urls(
        [
            "https://example.com/video1",  # valid
            "ftp://example.com/video2",  # invalid
            "not-a-url",  # invalid
            "http://example.com/video3",  # valid
            "",  # empty
            "   ",  # only spaces
        ]
    )
    expected = [
        "https://example.com/video1",
        "http://example.com/video3",
    ]
    assert mixed_urls == expected


def test_validate_urls_empty() -> None:
    """Test validation of empty URL list."""
    assert validate_urls([]) == []


def test_validate_urls_whitespace() -> None:
    """Test validation of URLs with whitespace."""
    whitespace_urls = validate_urls(
        [
            "  https://example.com/video1  ",
            "https://example.com/video2",
            "  http://example.com/video3  ",
        ]
    )
    expected = [
        "https://example.com/video1",
        "https://example.com/video2",
        "http://example.com/video3",
    ]
    assert whitespace_urls == expected
