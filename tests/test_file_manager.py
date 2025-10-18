"""Tests for file management module."""

import tempfile
from pathlib import Path

from src.file_manager import FileManager


def test_get_partial_paths() -> None:
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


def test_should_skip_download() -> None:
    """Test skip download check functionality."""
    fm = FileManager()

    # Test file does not exist
    test_path = Path("/tmp/nonexistent.mp4")
    assert not fm.should_skip_download(test_path)

    # Test file exists
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        test_path = Path(f.name)
        try:
            assert fm.should_skip_download(test_path)
        finally:
            test_path.unlink(missing_ok=True)


def test_remove_partials() -> None:
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


def test_cleanup_artifacts() -> None:
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


def test_sweep_leftovers() -> None:
    """Test comprehensive sweep leftovers functionality."""
    fm = FileManager()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create main file and various artifacts
        main_file = tmpdir_path / "video.mp4"
        sidecar_file = tmpdir_path / "video.mp4.ytdl"
        partial_file = tmpdir_path / "video.mp4.part"
        orphan_file = tmpdir_path / "orphan.ytdl"  # No main file
        unrelated = tmpdir_path / "other.txt"

        main_file.write_text("main content")
        sidecar_file.write_text("sidecar content")
        partial_file.write_text("partial content")
        orphan_file.write_text("orphan content")
        unrelated.write_text("unrelated")

        # Clean up remaining files
        fm.sweep_leftovers(tmpdir_path)

        # Check result
        assert main_file.exists()  # Main file should remain
        assert unrelated.exists()  # Unrelated file should remain
        assert not sidecar_file.exists()  # Artifacts should be removed
        assert not partial_file.exists()
        assert orphan_file.exists()  # Orphan file should remain
