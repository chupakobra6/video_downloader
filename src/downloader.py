"""Основной модуль скачивания видео."""

import asyncio
import logging
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError

from .browser import BrowserProfileManager
from .playwright_capture import PlaywrightCapture
from .file_manager import FileManager

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Основной класс для скачивания видео."""
    
    def __init__(
        self,
        browser: str = "chrome",
        browser_profile: Optional[str] = None,
        cookies_file: Optional[Path] = None,
    ):
        self.browser = browser
        self.browser_profile = browser_profile
        self.cookies_file = cookies_file
        self.profile_manager = BrowserProfileManager(browser)
        self.file_manager = FileManager()
        self.playwright_capture = PlaywrightCapture()
        
        # Статистика по доменам
        self.domain_stats: dict[str, dict[str, int]] = {}
        
    def _ensure_output_dir(self, base_dir: Path, url: str) -> Path:
        """Создать директорию для скачивания по домену."""
        parsed = urlparse(url)
        domain = parsed.netloc or "unknown-domain"
        destination = base_dir / domain
        destination.mkdir(parents=True, exist_ok=True)
        return destination
    
    def _build_ydl_opts(self, output_dir: Path, url: str) -> dict:
        """Построить опции для yt-dlp."""
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        
        ydl_opts: dict = {
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
        
        # Настройка куки
        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)
            logger.info("Using cookies file", extra={"path": str(self.cookies_file)})
        else:
            resolved_profile = self.profile_manager.find_profile_name(self.browser_profile)
            if resolved_profile is None:
                logger.info("Using default browser profile", extra={"browser": self.browser})
                ydl_opts["cookiesfrombrowser"] = (self.browser, None, None, None)
            else:
                profile_info = self.profile_manager.get_profile_info(resolved_profile)
                logger.info(
                    "Using browser profile",
                    extra={
                        "browser": self.browser,
                        "profile": resolved_profile,
                        "display_name": profile_info["display_name"],
                    },
                )
                ydl_opts["cookiesfrombrowser"] = (self.browser, resolved_profile, None, None)
                
        return ydl_opts
    
    def _download_with_ytdl(self, url: str, output_dir: Path) -> Optional[Path]:
        """Скачать видео через yt-dlp."""
        logger.info("START ytdl_download", extra={"url": url, "output_dir": str(output_dir)})
        
        try:
            ydl_opts = self._build_ydl_opts(output_dir, url)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Проверка поддержки URL
                try:
                    probe_info = ydl.extract_info(url, download=False)
                    expected_path = Path(ydl.prepare_filename(probe_info))
                    
                    # Проверка на существующий файл
                    if self.file_manager.should_skip_download(expected_path):
                        logger.info("DONE ytdl_download - already exists", extra={"file": str(expected_path)})
                        return expected_path
                        
                except DownloadError as e:
                    if "Unsupported URL" in str(e) or "does not pass URL" in str(e):
                        logger.info("FAIL ytdl_download - unsupported URL", extra={"url": url})
                        return None
                    raise
                
                # Скачивание
                ydl.extract_info(url, download=True)
                logger.info("DONE ytdl_download", extra={"file": str(expected_path)})
                return expected_path
                
        except DownloadError as e:
            logger.exception("FAIL ytdl_download", extra={"url": url, "error": str(e)})
            return None
    
    def _download_with_playwright(self, url: str, output_dir: Path) -> Optional[Path]:
        """Скачать видео через браузер (для DRM или нестандартных случаев)."""
        logger.info("START playwright_download", extra={"url": url, "output_dir": str(output_dir)})
        
        try:
            resolved_profile = self.profile_manager.find_profile_name(self.browser_profile)
            result = asyncio.run(
                self.playwright_capture.attempt_browser_download(
                    url=url,
                    browser=self.browser,
                    resolved_profile=resolved_profile,
                    output_dir=output_dir,
                    wait_timeout_sec=180,
                )
            )
            
            if result and result.exists():
                logger.info("DONE playwright_download", extra={"file": str(result)})
                return result
            else:
                logger.info("FAIL playwright_download - no file saved", extra={"url": url})
                return None
                
        except Exception as e:
            logger.exception("FAIL playwright_download", extra={"url": url, "error": str(e)})
            return None
    
    def download_video(self, url: str, base_output_dir: Path) -> Optional[Path]:
        """Скачать одно видео с fallback стратегией."""
        logger.info("START download_video", extra={"url": url})
        
        try:
            destination = self._ensure_output_dir(base_output_dir, url)
            parsed = urlparse(url)
            domain = parsed.netloc or "unknown-domain"
            
            # Инициализация статистики домена
            if domain not in self.domain_stats:
                self.domain_stats[domain] = {"total": 0, "success": 0}
            self.domain_stats[domain]["total"] += 1
            
            # Очистка старых артефактов
            self.file_manager.sweep_leftovers(destination)
            
            # Попытка скачивания через yt-dlp
            result = self._download_with_ytdl(url, destination)
            
            if result is None:
                # Fallback на браузерное скачивание
                logger.info("Trying browser download fallback", extra={"url": url})
                result = self._download_with_playwright(url, destination)
            
            if result and result.exists():
                self.domain_stats[domain]["success"] += 1
                logger.info("DONE download_video", extra={"url": url, "file": str(result)})
                return result
            else:
                logger.info("FAIL download_video - no file downloaded", extra={"url": url})
                return None
                
        except Exception as e:
            logger.exception("FAIL download_video", extra={"url": url, "error": str(e)})
            return None
    
    def download_videos(self, urls: Iterable[str], base_output_dir: Path) -> None:
        """Скачать множество видео."""
        logger.info("START download_videos", extra={"count": len(list(urls))})
        
        downloaded_files: dict[str, list[str]] = {}
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            result = self.download_video(url, base_output_dir)
            if result:
                domain = urlparse(url).netloc or "unknown-domain"
                if domain not in downloaded_files:
                    downloaded_files[domain] = []
                downloaded_files[domain].append(result.stem)
        
        # Создание файлов с названиями для успешно скачанных доменов
        self._create_titles_files(base_output_dir, downloaded_files)
        
        logger.info("DONE download_videos", extra={"stats": self.domain_stats})
    
    def _create_titles_files(self, base_output_dir: Path, downloaded_files: dict[str, list[str]]) -> None:
        """Создать файлы с названиями скачанных видео."""
        for domain, files in downloaded_files.items():
            domain_stats = self.domain_stats.get(domain, {"total": 0, "success": 0})
            if domain_stats["total"] > 0 and domain_stats["success"] == domain_stats["total"]:
                try:
                    out_dir = base_output_dir / domain
                    out_dir.mkdir(parents=True, exist_ok=True)
                    titles_path = out_dir / "titles.txt"
                    content = "\n".join(files) + "\n"
                    titles_path.write_text(content, encoding="utf-8")
                    logger.info(
                        "Created titles file",
                        extra={
                            "domain": domain,
                            "path": str(titles_path),
                            "count": len(files),
                        },
                    )
                except Exception as e:
                    logger.exception("Failed to create titles file", extra={"domain": domain, "error": str(e)})
