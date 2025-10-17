"""Tests for file management module."""

import tempfile
from pathlib import Path
import pytest

from src.file_manager import FileManager


def test_file_manager_init():
    """Test FileManager initialization."""
    fm = FileManager()
    assert fm is not None


def test_get_partial_paths():
    """Test getting paths to partial files."""
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
    """Test skip download check - file does not exist."""
    fm = FileManager()
    test_path = Path("/tmp/nonexistent.mp4")
    
    assert not fm.should_skip_download(test_path)


def test_should_skip_download_existing_file():
    """Test skip download check - file exists."""
    fm = FileManager()
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        test_path = Path(f.name)
        
        try:
            assert fm.should_skip_download(test_path)
        finally:
            test_path.unlink(missing_ok=True)


def test_remove_partials():
    """Test removal of partial files."""
    fm = FileManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / "test.mp4"
        
        # Create partial files
        partial_paths = fm._get_partial_paths(base_path)
        for partial_path in partial_paths:
            partial_path.write_text("test content")
            assert partial_path.exists()
        
        # Remove partial files
        fm._remove_partials(base_path)
        
        # Check that they are removed
        for partial_path in partial_paths:
            assert not partial_path.exists()


def test_cleanup_artifacts():
    """Test artifact cleanup."""
    fm = FileManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / "test.mp4"
        base_path.write_text("test content")
        
        # Create artifacts
        artifact1 = Path(tmpdir) / "test.mp4.part-001"
        artifact2 = Path(tmpdir) / "test.mp4.ytdl"
        artifact1.write_text("artifact1")
        artifact2.write_text("artifact2")
        
        assert artifact1.exists()
        assert artifact2.exists()
        
        # Clean up artifacts
        fm._cleanup_artifacts(base_path)
        
        # Check that artifacts are removed
        assert not artifact1.exists()
        assert not artifact2.exists()
        assert base_path.exists()  # Main file should remain


def test_sweep_leftovers():
    """Test cleanup of remaining files in directory."""
    fm = FileManager()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create main file and artifacts
        main_file = tmpdir_path / "video.mp4"
        artifact1 = tmpdir_path / "video.mp4.part-001"
        artifact2 = tmpdir_path / "video.mp4.ytdl"  # Fixed: should match main file
        unrelated = tmpdir_path / "other.txt"
        
        main_file.write_text("main content")
        artifact1.write_text("artifact1")
        artifact2.write_text("artifact2")
        unrelated.write_text("unrelated")
        
        assert main_file.exists()
        assert artifact1.exists()
        assert artifact2.exists()
        assert unrelated.exists()
        
        # Clean up remaining files
        fm.sweep_leftovers(tmpdir_path)
        
        # Check result
        assert main_file.exists()  # Main file should remain
        assert unrelated.exists()  # Unrelated file should remain
        assert not artifact1.exists()  # Artifacts should be removed
        assert not artifact2.exists()
