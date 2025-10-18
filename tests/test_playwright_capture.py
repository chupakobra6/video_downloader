"""Tests for Playwright capture functionality."""

from unittest.mock import Mock, patch

from src.playwright_capture import PlaywrightCapture


def test_http_get_text() -> None:
    """Test HTTP GET request functionality."""
    capture = PlaywrightCapture()

    # Test successful request
    with patch("src.playwright_capture.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "test content"
        mock_get.return_value = mock_response

        result = capture._http_get_text("https://example.com", None)
        assert result == "test content"

    # Test error status
    with patch("src.playwright_capture.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = capture._http_get_text("https://example.com", None)
        assert result is None

    # Test exception
    with patch("src.playwright_capture.requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        result = capture._http_get_text("https://example.com", None)
        assert result is None


def test_detect_drm_in_m3u8_comprehensive() -> None:
    """Test comprehensive DRM detection in M3U8."""
    capture = PlaywrightCapture()

    # Test no DRM
    with patch.object(capture, "_http_get_text") as mock_get:
        mock_get.return_value = "#EXTM3U\n#EXTINF:10.0\nvideo.ts"
        has_drm, error = capture.detect_drm_in_m3u8(
            "https://example.com/playlist.m3u8", None
        )
        assert has_drm is False
        assert error is None

    # Test SAMPLE-AES DRM
    with patch.object(capture, "_http_get_text") as mock_get:
        mock_get.return_value = (
            "#EXTM3U\n#EXT-X-SESSION-KEY:METHOD=SAMPLE-AES\nvideo.ts"
        )
        has_drm, error = capture.detect_drm_in_m3u8(
            "https://example.com/playlist.m3u8", None
        )
        assert has_drm is True
        assert error == "SAMPLE-AES(session)"

    # Test AES-128 (not DRM)
    with patch.object(capture, "_http_get_text") as mock_get:
        mock_get.return_value = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128\nvideo.ts"
        has_drm, error = capture.detect_drm_in_m3u8(
            "https://example.com/playlist.m3u8", None
        )
        assert has_drm is False
        assert error == "AES-128"

    # Test error case
    with patch.object(capture, "_http_get_text") as mock_get:
        mock_get.return_value = None
        has_drm, error = capture.detect_drm_in_m3u8(
            "https://example.com/playlist.m3u8", None
        )
        assert has_drm is False
        assert error is None
