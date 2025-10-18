"""Tests for video downloader."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.downloader import VideoDownloader


@patch("src.downloader.PlaywrightCapture")
def test_ensure_output_dir(mock_playwright: Mock) -> None:
    """Test creating output directory by domain."""
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = VideoDownloader()
        base_dir = Path(temp_dir)

        result = downloader._ensure_output_dir(base_dir, "https://example.com/video")
        expected = base_dir / "example.com"
        assert result == expected
        assert result.exists()
        assert result.is_dir()


@patch("src.downloader.PlaywrightCapture")
def test_ensure_output_dir_unknown_domain(mock_playwright: Mock) -> None:
    """Test creating output directory for unknown domain."""
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = VideoDownloader()
        base_dir = Path(temp_dir)

        result = downloader._ensure_output_dir(base_dir, "invalid-url")
        expected = base_dir / "unknown-domain"
        assert result == expected
        assert result.exists()
        assert result.is_dir()


@patch("src.downloader.PlaywrightCapture")
def test_build_ydl_opts_with_profile(mock_playwright: Mock) -> None:
    """Test building yt-dlp options with Chrome profile."""
    downloader = VideoDownloader(browser_profile="Test Profile")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        opts = downloader._build_ydl_opts(output_dir, "https://example.com/video")

        assert "cookiesfrombrowser" in opts
        assert opts["cookiesfrombrowser"][0] == "chrome"


@patch("src.downloader.PlaywrightCapture")
def test_build_ydl_opts_without_profile(mock_playwright: Mock) -> None:
    """Test building yt-dlp options without profile (default Chrome)."""
    downloader = VideoDownloader()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        opts = downloader._build_ydl_opts(output_dir, "https://example.com/video")

        assert "cookiesfrombrowser" in opts
        assert opts["cookiesfrombrowser"][0] == "chrome"


@patch("src.downloader.yt_dlp.YoutubeDL")
def test_download_with_ytdl_unsupported_url(mock_ydl_class: Mock) -> None:
    """Test download with unsupported URL."""
    # Setup mock
    mock_ydl = Mock()
    mock_ydl_class.return_value.__enter__.return_value = mock_ydl

    # Mock extract_info to raise unsupported URL error
    from yt_dlp.utils import DownloadError

    mock_ydl.extract_info.side_effect = DownloadError("Unsupported URL")

    downloader = VideoDownloader()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        result = downloader._download_with_ytdl(
            "https://unsupported.com/video", output_dir
        )

        assert result is None


@patch("src.downloader.PlaywrightCapture")
def test_download_video_core_logic(mock_playwright: Mock) -> None:
    """Test core video download logic and statistics."""
    downloader = VideoDownloader()

    with patch.object(downloader, "_download_with_ytdl") as mock_ytdl:
        mock_file = Path("/tmp/video.mp4")
        mock_ytdl.return_value = mock_file

        # Mock file.exists() to return True
        with patch.object(Path, "exists", return_value=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                base_dir = Path(temp_dir)
                result = downloader.download_video(
                    "https://example.com/video", base_dir
                )

                assert result == mock_file
                assert "example.com" in downloader.domain_stats
                assert downloader.domain_stats["example.com"]["total"] == 1
                assert downloader.domain_stats["example.com"]["success"] == 1


@patch("src.downloader.PlaywrightCapture")
def test_create_titles_files(mock_playwright: Mock) -> None:
    """Test creating titles files for successful downloads."""
    downloader = VideoDownloader()
    downloader.domain_stats = {
        "example.com": {"total": 2, "success": 2},
        "test.com": {"total": 1, "success": 0},
    }

    downloaded_files = {"example.com": ["video1", "video2"], "test.com": ["video3"]}

    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)

        # Create domain directories
        (base_dir / "example.com").mkdir()
        (base_dir / "test.com").mkdir()

        downloader._create_titles_files(base_dir, downloaded_files)

        # Check that titles file was created for successful domain
        titles_file = base_dir / "example.com" / "titles.txt"
        assert titles_file.exists()

        content = titles_file.read_text()
        assert "video1" in content
        assert "video2" in content

        # Check that no titles file was created for failed domain
        test_titles_file = base_dir / "test.com" / "titles.txt"
        assert not test_titles_file.exists()


@patch("src.downloader.PlaywrightCapture")
def test_download_with_ytdl_exception(mock_playwright: Mock) -> None:
    """Test download with yt-dlp exception."""
    downloader = VideoDownloader()

    with patch("src.downloader.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = Mock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock extract_info to raise exception
        from yt_dlp.utils import DownloadError

        mock_ydl.extract_info.side_effect = DownloadError("Network error")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            result = downloader._download_with_ytdl(
                "https://example.com/video", output_dir
            )

            assert result is None


@patch("src.downloader.PlaywrightCapture")
def test_download_video_no_valid_url(mock_playwright: Mock) -> None:
    """Test downloading video with invalid URL."""
    downloader = VideoDownloader()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        result = downloader.download_video("invalid-url", base_dir)

        # Should return None for invalid URL
        assert result is None


@patch("src.downloader.PlaywrightCapture")
def test_download_videos_batch_logic(mock_playwright: Mock) -> None:
    """Test batch video download logic."""
    downloader = VideoDownloader()

    with patch.object(downloader, "download_video") as mock_download:
        mock_download.return_value = Path("/tmp/video.mp4")

        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            urls = [
                "https://example.com/video1",
                "https://test.com/video2",
                "https://example.com/video3",
            ]
            downloader.download_videos(urls, base_dir)

            assert mock_download.call_count == 3
            # Test empty list doesn't crash
            downloader.download_videos([], base_dir)
