"""Tests for utilities."""

import tempfile
from pathlib import Path
import pytest

from src.utils import read_links_file, validate_urls


def test_read_links_file_existing():
    """Test reading existing links file."""
    content = """
# Comment
https://example.com/video1
https://example.com/video2

# Another comment
https://example.com/video3
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
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


def test_read_links_file_nonexistent():
    """Test reading non-existent links file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        links_path = Path(tmpdir) / "nonexistent.txt"
        
        links = read_links_file(links_path)
        assert links == []
        
        # Check that template file was created
        assert links_path.exists()
        content = links_path.read_text(encoding="utf-8")
        assert "# Add your URLs here, one per line" in content


def test_read_links_file_empty():
    """Test reading empty links file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("")
        f.flush()
        
        try:
            links = read_links_file(Path(f.name))
            assert links == []
        finally:
            Path(f.name).unlink()


def test_read_links_file_only_comments():
    """Test reading file with only comments."""
    content = """
# Only comments
# No links
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        f.flush()
        
        try:
            links = read_links_file(Path(f.name))
            assert links == []
        finally:
            Path(f.name).unlink()


def test_validate_urls_valid():
    """Test validation of valid URLs."""
    urls = [
        "https://example.com/video1",
        "http://example.com/video2",
        "https://youtube.com/watch?v=123",
    ]
    
    valid_urls = validate_urls(urls)
    assert valid_urls == urls


def test_validate_urls_invalid():
    """Test validation of invalid URLs."""
    urls = [
        "https://example.com/video1",  # valid
        "ftp://example.com/video2",   # invalid
        "not-a-url",                   # invalid
        "http://example.com/video3",   # valid
        "",                            # empty
        "   ",                         # only spaces
    ]
    
    valid_urls = validate_urls(urls)
    expected = [
        "https://example.com/video1",
        "http://example.com/video3",
    ]
    assert valid_urls == expected


def test_validate_urls_empty():
    """Test validation of empty URL list."""
    urls = []
    valid_urls = validate_urls(urls)
    assert valid_urls == []


def test_validate_urls_with_whitespace():
    """Test validation of URLs with spaces."""
    urls = [
        "  https://example.com/video1  ",
        "https://example.com/video2",
        "  http://example.com/video3  ",
    ]
    
    valid_urls = validate_urls(urls)
    expected = [
        "https://example.com/video1",
        "https://example.com/video2",
        "http://example.com/video3",
    ]
    assert valid_urls == expected
