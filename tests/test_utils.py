"""Тесты для утилит."""

import tempfile
from pathlib import Path
import pytest

from src.utils import read_links_file, validate_urls


def test_read_links_file_existing():
    """Тест чтения существующего файла с ссылками."""
    content = """
# Комментарий
https://example.com/video1
https://example.com/video2

# Еще комментарий
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
    """Тест чтения несуществующего файла с ссылками."""
    with tempfile.TemporaryDirectory() as tmpdir:
        links_path = Path(tmpdir) / "nonexistent.txt"
        
        links = read_links_file(links_path)
        assert links == []
        
        # Проверяем, что создался шаблонный файл
        assert links_path.exists()
        content = links_path.read_text(encoding="utf-8")
        assert "# Add your URLs here, one per line" in content


def test_read_links_file_empty():
    """Тест чтения пустого файла с ссылками."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("")
        f.flush()
        
        try:
            links = read_links_file(Path(f.name))
            assert links == []
        finally:
            Path(f.name).unlink()


def test_read_links_file_only_comments():
    """Тест чтения файла только с комментариями."""
    content = """
# Только комментарии
# Без ссылок
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
    """Тест валидации валидных URL."""
    urls = [
        "https://example.com/video1",
        "http://example.com/video2",
        "https://youtube.com/watch?v=123",
    ]
    
    valid_urls = validate_urls(urls)
    assert valid_urls == urls


def test_validate_urls_invalid():
    """Тест валидации невалидных URL."""
    urls = [
        "https://example.com/video1",  # валидный
        "ftp://example.com/video2",   # невалидный
        "not-a-url",                   # невалидный
        "http://example.com/video3",   # валидный
        "",                            # пустой
        "   ",                         # только пробелы
    ]
    
    valid_urls = validate_urls(urls)
    expected = [
        "https://example.com/video1",
        "http://example.com/video3",
    ]
    assert valid_urls == expected


def test_validate_urls_empty():
    """Тест валидации пустого списка URL."""
    urls = []
    valid_urls = validate_urls(urls)
    assert valid_urls == []


def test_validate_urls_with_whitespace():
    """Тест валидации URL с пробелами."""
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
