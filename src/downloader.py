"""Simple video downloader using yt-dlp."""

import logging
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Simple video downloader."""

    def __init__(self) -> None:
        self.domain_stats: dict[str, dict[str, int]] = {}

    def _ensure_output_dir(self, base_dir: Path, url: str) -> Path:
        """Create download directory by domain."""
        parsed = urlparse(url)
        domain: str = parsed.netloc or "unknown-domain"
        destination: Path = base_dir / domain
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    def _build_ydl_opts(self, output_dir: Path, url: str) -> dict[str, Any]:
        """Build options for yt-dlp."""
        parsed = urlparse(url)
        origin: str = f"{parsed.scheme}://{parsed.netloc}"

        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": str(output_dir / "%(title).100B.%(ext)s"),
            "trim_file_name": 120,
            "outtmpl_na_placeholder": "NA",
            "writesubtitles": False,
            "writeinfojson": False,
            "writedescription": False,
            "writethumbnail": False,
            "restrictfilenames": False,
            "concurrent_fragment_downloads": 8,
            "continuedl": True,
            "ignoreerrors": False,
            "noprogress": False,
            "http_headers": {
                "Referer": url,
                "Origin": origin,
            },
            "merge_output_format": "mp4",
            "postprocessors": [
                {"key": "FFmpegMetadata", "add_metadata": True},
            ],
            "postprocessor_args": ["-movflags", "+faststart"],
            "prefer_ffmpeg": True,
            "overwrites": False,
            "check_formats": True,
        }

        # Configure cookies from Chrome profile
        ydl_opts["cookiesfrombrowser"] = ("chrome", None, None, None)

        return ydl_opts

    def download_video(self, url: str, output_dir: Path) -> Optional[Path]:
        """Download a single video."""
        logger.info("START download_video", extra={"url": url})

        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logger.warning("Invalid URL format", extra={"url": url})
                return None

            domain: str = parsed.netloc or "unknown-domain"

            # Initialize domain statistics
            if domain not in self.domain_stats:
                self.domain_stats[domain] = {"total": 0, "success": 0}
            self.domain_stats[domain]["total"] += 1

            # Build yt-dlp options
            ydl_opts: dict[str, Any] = self._build_ydl_opts(output_dir, url)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Check URL support
                try:
                    probe_info: dict[str, Any] = ydl.extract_info(url, download=False)
                    expected_path: Path = Path(ydl.prepare_filename(probe_info))

                    # Check for existing file
                    if expected_path.exists():
                        logger.info(
                            "DONE download_video - already exists",
                            extra={"file": str(expected_path)},
                        )
                        self.domain_stats[domain]["success"] += 1
                        return expected_path

                except DownloadError as e:
                    if "Unsupported URL" in str(e) or "does not pass URL" in str(e):
                        logger.info(
                            "FAIL download_video - unsupported URL", extra={"url": url}
                        )
                        return None
                    raise

                # Download
                ydl.extract_info(url, download=True)
                logger.info("DONE download_video", extra={"file": str(expected_path)})
                self.domain_stats[domain]["success"] += 1
                return expected_path

        except DownloadError as e:
            logger.exception("FAIL download_video", extra={"url": url, "error": str(e)})
            return None
        except Exception as e:
            logger.exception("FAIL download_video", extra={"url": url, "error": str(e)})
            return None

    def download_videos(self, urls: Iterable[str], base_output_dir: Path) -> None:
        """Download multiple videos."""
        urls_list = list(urls)
        logger.info("START download_videos", extra={"count": len(urls_list)})

        for url in urls_list:
            url = url.strip()
            if not url:
                continue

            destination: Path = self._ensure_output_dir(base_output_dir, url)
            self.download_video(url, destination)

        logger.info("DONE download_videos", extra={"stats": self.domain_stats})
