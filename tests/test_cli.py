"""Tests for CLI interface."""

import tempfile
from pathlib import Path

from src.cli import parse_args, resolve_urls


def test_parse_args_default() -> None:
    """Test parsing default arguments."""
    args = parse_args([])
    assert args.inputs == []
    assert args.browser_profile is None
    assert args.output_root == "downloads"
    assert args.config == "config.toml"
    assert args.verbose is False


def test_parse_args_with_urls() -> None:
    """Test parsing arguments with URLs."""
    args = parse_args(["https://example.com", "https://test.com"])
    assert args.inputs == ["https://example.com", "https://test.com"]


def test_parse_args_with_options() -> None:
    """Test parsing arguments with options."""
    args = parse_args(
        [
            "--browser-profile",
            "Profile 1",
            "--output-root",
            "/tmp/downloads",
            "--config",
            "custom.toml",
            "--verbose",
            "https://example.com",
        ]
    )
    assert args.browser_profile == "Profile 1"
    assert args.output_root == "/tmp/downloads"
    assert args.config == "custom.toml"
    assert args.verbose is True
    assert args.inputs == ["https://example.com"]


def test_resolve_urls_comprehensive() -> None:
    """Test comprehensive URL resolution functionality."""
    # Test direct URLs
    urls = resolve_urls(["https://example.com", "https://test.com"])
    assert urls == ["https://example.com", "https://test.com"]

    # Test file path
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("https://example.com\nhttps://test.com\n")
        f.flush()

        urls = resolve_urls([f.name])
        assert "https://example.com" in urls
        assert "https://test.com" in urls

        Path(f.name).unlink()

    # Test mixed URLs and file paths
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("https://file.com\n")
        f.flush()

        urls = resolve_urls(["https://direct.com", f.name])
        assert "https://direct.com" in urls
        assert "https://file.com" in urls

        Path(f.name).unlink()

    # Test nonexistent file
    urls = resolve_urls(["/nonexistent/file.txt"])
    assert urls == ["/nonexistent/file.txt"]
