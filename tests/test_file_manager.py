"""Тесты для модуля управления файлами."""

import tempfile
from pathlib import Path
import pytest

from src.file_manager import FileManager


def test_file_manager_init():
    """Тест инициализации FileManager."""
    fm = FileManager()
    assert fm is not None


def test_get_partial_paths():
    """Тест получения путей к частичным файлам."""
    fm = FileManager()
    test_path = Path("/tmp/test.mp4")
    partials = fm._get_partial_paths(test_path)
    
    expected = [
        Path("/tmp/test.mp4.part"),
        Path("/tmp/test.mp4.ytdl"),
        Path("/tmp/test.part"),
    ]
    
    assert len(partials) == len(expected)
    for expected_path in expected:
        assert expected_path in partials


def test_should_skip_download_no_file():
    """Тест проверки пропуска скачивания - файл не существует."""
    fm = FileManager()
    test_path = Path("/tmp/nonexistent.mp4")
    
    assert not fm.should_skip_download(test_path)


def test_should_skip_download_existing_file():
    """Тест проверки пропуска скачивания - файл существует."""
    fm = FileManager()
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        test_path = Path(f.name)
        
        try:
            assert fm.should_skip_download(test_path)
        finally:
            test_path.unlink(missing_ok=True)


def test_remove_partials():
    """Тест удаления частичных файлов."""
    fm = FileManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / "test.mp4"
        
        # Создаем частичные файлы
        partial_paths = fm._get_partial_paths(base_path)
        for partial_path in partial_paths:
            partial_path.write_text("test content")
            assert partial_path.exists()
        
        # Удаляем частичные файлы
        fm._remove_partials(base_path)
        
        # Проверяем, что они удалены
        for partial_path in partial_paths:
            assert not partial_path.exists()


def test_cleanup_artifacts():
    """Тест очистки артефактов."""
    fm = FileManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / "test.mp4"
        base_path.write_text("test content")
        
        # Создаем артефакты
        artifact1 = Path(tmpdir) / "test.mp4.part-001"
        artifact2 = Path(tmpdir) / "test.mp4.ytdl"
        artifact1.write_text("artifact1")
        artifact2.write_text("artifact2")
        
        assert artifact1.exists()
        assert artifact2.exists()
        
        # Очищаем артефакты
        fm._cleanup_artifacts(base_path)
        
        # Проверяем, что артефакты удалены
        assert not artifact1.exists()
        assert not artifact2.exists()
        assert base_path.exists()  # Основной файл должен остаться


def test_sweep_leftovers():
    """Тест очистки оставшихся файлов в директории."""
    fm = FileManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Создаем основной файл и артефакты
        main_file = tmpdir_path / "video.mp4"
        artifact1 = tmpdir_path / "video.mp4.part-001"
        artifact2 = tmpdir_path / "video.mp4.ytdl"  # Исправлено: должен соответствовать основному файлу
        unrelated = tmpdir_path / "other.txt"
        
        main_file.write_text("main content")
        artifact1.write_text("artifact1")
        artifact2.write_text("artifact2")
        unrelated.write_text("unrelated")
        
        assert main_file.exists()
        assert artifact1.exists()
        assert artifact2.exists()
        assert unrelated.exists()
        
        # Очищаем оставшиеся файлы
        fm.sweep_leftovers(tmpdir_path)
        
        # Проверяем результат
        assert main_file.exists()  # Основной файл должен остаться
        assert unrelated.exists()  # Несвязанный файл должен остаться
        assert not artifact1.exists()  # Артефакты должны быть удалены
        assert not artifact2.exists()
