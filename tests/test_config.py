"""Tests for configuration module."""

import tempfile
from pathlib import Path

from src.config import Config


def test_config_default() -> None:
    """Test default configuration creation."""
    config = Config()
    assert config.browser_profile is None
    assert config.output_root == Path("downloads")
    assert config.links_file == Path("links.txt")


def test_config_custom() -> None:
    """Test custom configuration creation."""
    config = Config(
        browser_profile="Test Profile",
        output_root=Path("/tmp"),
        links_file=Path("custom_links.txt"),
    )
    assert config.browser_profile == "Test Profile"
    assert config.output_root == Path("/tmp")
    assert config.links_file == Path("custom_links.txt")


def test_config_from_toml() -> None:
    """Test loading configuration from TOML."""
    toml_content = """
browser_profile = "Test User"
output_root = "test_downloads"
links_file = "test_links.txt"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        f.flush()

        try:
            config = Config.from_toml(Path(f.name), Path.cwd())
            assert config.browser_profile == "Test User"
            assert config.output_root == Path("test_downloads")
            assert config.links_file == Path.cwd() / "test_links.txt"
        finally:
            Path(f.name).unlink()


def test_config_validation() -> None:
    """Test configuration validation."""
    # Test valid configuration
    config = Config()
    config.validate()  # Should not raise exception
