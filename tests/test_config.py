"""Тесты для модуля конфигурации."""

import tempfile
from pathlib import Path
import pytest

from src.config import Config


def test_config_default():
    """Тест создания конфигурации по умолчанию."""
    config = Config()
    assert config.browser == "chrome"
    assert config.browser_profile is None
    assert config.output_root == Path("downloads")
    assert config.links_file == Path("links.txt")
    assert config.cookies_file is None


def test_config_custom():
    """Тест создания кастомной конфигурации."""
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
    """Тест загрузки конфигурации из TOML."""
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
    """Тест валидации валидной конфигурации."""
    config = Config(browser="chrome")
    # Не должно вызывать исключение
    config.validate()


def test_config_validation_invalid_browser():
    """Тест валидации невалидного браузера."""
    config = Config(browser="invalid_browser")
    with pytest.raises(ValueError, match="Invalid browser"):
        config.validate()


def test_config_validation_missing_cookies_file():
    """Тест валидации с отсутствующим файлом куки."""
    config = Config(cookies_file=Path("nonexistent_cookies.txt"))
    # Не должно вызывать исключение, только предупреждение
    config.validate()
