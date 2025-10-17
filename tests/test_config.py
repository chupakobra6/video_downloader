"""Tests for configuration module."""

import tempfile
from pathlib import Path
import pytest

from src.config import Config


def test_config_default():
    """Test default configuration creation."""
    config = Config()
    assert config.browser == "chrome"
    assert config.browser_profile is None
    assert config.output_root == Path("downloads")
    assert config.links_file == Path("links.txt")
    assert config.cookies_file is None


def test_config_custom():
    """Test custom configuration creation."""
    config = Config(
        browser="edge",
        browser_profile="Test Profile",
        output_root=Path("/tmp"),
        links_file=Path("custom_links.txt"),
        cookies_file=Path("cookies.txt"),
    )
    assert config.browser == "edge"
    assert config.browser_profile == "Test Profile"
    assert config.output_root == Path("/tmp")
    assert config.links_file == Path("custom_links.txt")
    assert config.cookies_file == Path("cookies.txt")


def test_config_from_toml():
    """Test loading configuration from TOML."""
    toml_content = """
browser = "brave"
browser_profile = "Test User"
output_root = "test_downloads"
links_file = "test_links.txt"
cookies_file = "test_cookies.txt"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        f.flush()
        
        try:
            config = Config.from_toml(Path(f.name), Path.cwd())
            assert config.browser == "brave"
            assert config.browser_profile == "Test User"
            assert config.output_root == Path("test_downloads")
            assert config.links_file == Path.cwd() / "test_links.txt"
            assert config.cookies_file == Path.cwd() / "test_cookies.txt"
        finally:
            Path(f.name).unlink()


def test_config_validation_valid():
    """Test validation of valid configuration."""
    config = Config(browser="chrome")
    # Should not raise exception
    config.validate()


def test_config_validation_invalid_browser():
    """Test validation of invalid browser."""
    config = Config(browser="invalid_browser")
    with pytest.raises(ValueError, match="Invalid browser"):
        config.validate()


def test_config_validation_missing_cookies_file():
    """Test validation with missing cookies file."""
    config = Config(cookies_file=Path("nonexistent_cookies.txt"))
    # Should not raise exception, only warning
    config.validate()
