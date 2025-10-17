"""Захват видео через Playwright для DRM и нестандартных случаев."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

logger = logging.getLogger(__name__)


class PlaywrightCapture:
    """Захват видео через браузер с помощью Playwright."""
    
    def __init__(self):
        if async_playwright is None:
            logger.warning("Playwright not available - browser capture disabled")
    
    def _get_chrome_like_base(self, browser: str) -> Optional[Path]:
        """Получить базовый путь к профилям браузера."""
        base: Optional[Path] = None
        match sys.platform:
            case "darwin":
                match browser:
                    case "chrome":
                        base = Path.home() / "Library/Application Support/Google/Chrome"
                    case "brave":
                        base = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"
                    case "edge":
                        base = Path.home() / "Library/Application Support/Microsoft Edge"
                    case "chromium":
                        base = Path.home() / "Library/Application Support/Chromium"
            case "linux" | "linux2":
                match browser:
                    case "chrome":
                        base = Path.home() / ".config/google-chrome"
                    case "brave":
                        base = Path.home() / ".config/BraveSoftware/Brave-Browser"
                    case "edge":
                        base = Path.home() / ".config/microsoft-edge"
                    case "chromium":
                        base = Path.home() / ".config/chromium"
        return base if base and base.exists() else None
    
    def _http_get_text(self, url: str, headers: Optional[dict[str, str]], timeout_sec: int = 30) -> Optional[str]:
        """Получить текст по HTTP."""
        try:
            resp = requests.get(url, headers=headers or {}, timeout=timeout_sec)
            if resp.status_code >= 400:
                return None
            return resp.text
        except Exception as e:
            logger.exception("HTTP GET failed", extra={"url": url, "error": str(e)})
            return None
    
    def detect_drm_in_m3u8(self, manifest_url: str, headers: Optional[dict[str, str]]) -> Tuple[bool, Optional[str]]:
        """Обнаружить DRM в HLS манифестах."""
        root = self._http_get_text(manifest_url, headers)
        if not root:
            return False, None
            
        text = root
        lower = text.lower()
        
        # Проверка на master манифест
        if "#ext-x-session-key" in lower and "sample-aes" in lower:
            return True, "SAMPLE-AES(session)"
        if "com.apple.fps" in lower or "fairplay" in lower:
            return True, "FairPlay"
        if "com.widevine.alpha" in lower or "widevine" in lower:
            return True, "Widevine"
        
        # Поиск variant URL для проверки
        variant_url: Optional[str] = None
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(".m3u8"):
                variant_url = urljoin(manifest_url, line)
                break
        
        if not variant_url:
            # Single-level манифест
            if "#ext-x-key" in lower:
                if "sample-aes" in lower:
                    return True, "SAMPLE-AES"
                if "aes-128" in lower:
                    return False, "AES-128"
            return False, None
        
        # Проверка variant манифеста
        variant = self._http_get_text(variant_url, headers)
        if not variant:
            return False, None
            
        vlow = variant.lower()
        if "#ext-x-key" in vlow:
            if "sample-aes" in vlow:
                return True, "SAMPLE-AES"
            if "com.apple.fps" in vlow or "fairplay" in vlow:
                return True, "FairPlay"
            if "com.widevine.alpha" in vlow or "widevine" in vlow:
                return True, "Widevine"
            if "aes-128" in vlow:
                return False, "AES-128"
                
        return False, None
    
    async def capture_stream_manifest(
        self,
        page_url: str,
        browser: str,
        resolved_profile: Optional[str],
        wait_timeout_sec: int = 45,
    ) -> Optional[Tuple[str, dict[str, str], Optional[str]]]:
        """Захватить манифест потока через браузер."""
        if async_playwright is None:
            return None
            
        logger.info("START capture_stream_manifest", extra={"url": page_url, "timeout": wait_timeout_sec})
        
        # Маппинг браузера на Playwright channel
        channel: Optional[str] = None
        match browser:
            case "chrome":
                channel = "chrome"
            case "edge":
                channel = "msedge"
        
        base = self._get_chrome_like_base(browser)
        user_data_dir: Optional[Path] = base if base and base.exists() else None
        
        launch_args: list[str] = []
        if resolved_profile:
            launch_args.append(f"--profile-directory={resolved_profile}")
        
        try:
            async with async_playwright() as p:
                context = None
                
                # Попытка использовать системный браузер с профилем
                if channel and user_data_dir is not None:
                    try:
                        context = await p.chromium.launch_persistent_context(
                            user_data_dir=str(user_data_dir),
                            channel=channel,
                            headless=False,
                            args=[
                                "--autoplay-policy=no-user-gesture-required",
                                *launch_args,
                            ],
                        )
                    except Exception as e:
                        logger.warning("Failed to launch system browser", extra={"error": str(e)})
                        context = None
                
                # Fallback на bundled chromium
                if context is None:
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=str(Path.cwd() / ".pw-temp-profile"),
                        headless=False,
                        args=["--autoplay-policy=no-user-gesture-required"],
                    )
                
                page = await context.new_page()
                
                # Настройка для автоплей
                try:
                    await page.add_init_script("""
                        Object.defineProperty(document, 'visibilityState', {get: () => 'visible'});
                        Object.defineProperty(document, 'hidden', {get: () => false});
                    """)
                except Exception:
                    pass
                
                # Захват манифеста
                found: asyncio.Future[Tuple[str, dict[str, str]]] = asyncio.get_event_loop().create_future()
                
                def _maybe_set(req_url: str, headers: dict[str, str]) -> None:
                    try:
                        if any(s in req_url for s in [".m3u8", ".mpd", "format=m3u8"]):
                            if not found.done():
                                found.set_result((req_url, headers))
                    except Exception:
                        pass
                
                page.on("request", lambda request: _maybe_set(request.url, request.headers))
                
                async def on_response(response):
                    try:
                        url = response.url
                        ctype = (response.headers or {}).get("content-type", "")
                        if any(s in url for s in [".m3u8", ".mpd"]) or (
                            "mpegurl" in ctype or "dash+xml" in ctype
                        ):
                            req = response.request
                            _maybe_set(url, req.headers)
                    except Exception:
                        pass
                
                page.on("response", on_response)
                
                await page.goto(page_url, wait_until="domcontentloaded")
                
                # Получение заголовка страницы
                page_title: Optional[str] = None
                try:
                    page_title = await page.title()
                except Exception:
                    pass
                
                # Попытка запустить воспроизведение
                selectors = [
                    "video",
                    "jugru-video video",
                    "button[aria-label='Воспроизвести']",
                    "[data-testid='play'], .play, .video-play",
                ]
                for sel in selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            await el.click(timeout=2000)
                    except Exception:
                        continue
                
                # Программный запуск видео
                try:
                    await page.evaluate("""
                        const v = document.querySelector('video');
                        if (v) { v.muted = true; v.play().catch(()=>{}); }
                    """)
                except Exception:
                    pass
                
                try:
                    logger.info("Waiting for video manifest", extra={"timeout_sec": wait_timeout_sec})
                    manifest_url, req_headers = await asyncio.wait_for(found, timeout=wait_timeout_sec)
                    await context.close()
                    logger.info("DONE capture_stream_manifest", extra={"manifest_url": manifest_url})
                    return manifest_url, req_headers, page_title
                except asyncio.TimeoutError:
                    await context.close()
                    logger.info("FAIL capture_stream_manifest - timeout", extra={"url": page_url})
                    return None
                    
        except Exception as e:
            logger.exception("FAIL capture_stream_manifest", extra={"url": page_url, "error": str(e)})
            return None
    
    async def attempt_browser_download(
        self,
        url: str,
        browser: str,
        resolved_profile: Optional[str],
        output_dir: Path,
        wait_timeout_sec: int = 180,
    ) -> Optional[Path]:
        """Попытка скачивания через браузер."""
        if async_playwright is None:
            return None
            
        logger.info("START attempt_browser_download", extra={"url": url, "timeout": wait_timeout_sec})
        
        # Маппинг браузера на Playwright channel
        channel: Optional[str] = None
        match browser:
            case "chrome":
                channel = "chrome"
            case "edge":
                channel = "msedge"
        
        base = self._get_chrome_like_base(browser)
        user_data_dir: Optional[Path] = base if base and base.exists() else None
        
        launch_args: list[str] = []
        if resolved_profile:
            launch_args.append(f"--profile-directory={resolved_profile}")
        
        try:
            async with async_playwright() as p:
                context = None
                
                # Попытка использовать системный браузер
                if channel and user_data_dir is not None:
                    try:
                        context = await p.chromium.launch_persistent_context(
                            user_data_dir=str(user_data_dir),
                            channel=channel,
                            headless=False,
                            args=[*launch_args],
                        )
                    except Exception as e:
                        logger.warning("Failed to launch system browser", extra={"error": str(e)})
                        context = None
                
                # Fallback на bundled chromium
                if context is None:
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=str(Path.cwd() / ".pw-temp-profile"),
                        headless=False,
                    )
                
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded")
                
                logger.info("Waiting for browser download", extra={"timeout_sec": wait_timeout_sec})
                
                try:
                    async with page.expect_download(timeout=wait_timeout_sec * 1000) as dl_info:
                        # Поиск iframe Kinescope
                        target_frame = None
                        try:
                            for fr in page.frames:
                                if "kinescope.io" in (fr.url or ""):
                                    target_frame = fr
                                    break
                        except Exception:
                            target_frame = None
                        
                        # Селекторы для кнопок скачивания
                        candidates = [
                            "button[aria-label*='Скачать']",
                            "button[aria-label*='скачать']",
                            "button[aria-label*='Download' i]",
                            "button:has-text('Скачать')",
                            "button:has-text('Download')",
                            "[data-testid='downloadsButton']",
                            "[data-testid='downloadButton']",
                            ".kin-pl-downloadsButton",
                            "[class*='downloads'] button",
                        ]
                        
                        async def _click_in(frame_obj):
                            for sel in candidates:
                                try:
                                    el = await frame_obj.query_selector(sel)
                                    if el:
                                        await el.click(timeout=2000)
                                        return True
                                except Exception:
                                    continue
                            return False
                        
                        # Клик в iframe или основной странице
                        clicked = False
                        if target_frame is not None:
                            clicked = await _click_in(target_frame)
                        if not clicked:
                            clicked = await _click_in(page)
                        
                        # Попытка клика по ссылке скачивания
                        if target_frame is not None and not clicked:
                            try:
                                link = await target_frame.query_selector("a[download], a[href*='.mp4']")
                                if link:
                                    await link.click(timeout=2000)
                                    clicked = True
                            except Exception:
                                pass
                        
                        if not clicked:
                            # Дать пользователю время для ручного клика
                            try:
                                await page.wait_for_timeout(1500)
                            except Exception:
                                pass
                    
                    download = await dl_info.value
                    suggested = download.suggested_filename or "download.bin"
                    safe_name = suggested.replace("/", "-").replace("\\", "-").strip()
                    target = output_dir / safe_name
                    await download.save_as(str(target))
                    await context.close()
                    
                    logger.info("DONE attempt_browser_download", extra={"file": str(target)})
                    return target
                    
                except Exception as e:
                    await context.close()
                    logger.info("FAIL attempt_browser_download - no download triggered", extra={"url": url, "error": str(e)})
                    return None
                    
        except Exception as e:
            logger.exception("FAIL attempt_browser_download", extra={"url": url, "error": str(e)})
            return None
