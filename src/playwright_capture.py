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
        
        try:
            async with async_playwright() as p:
                # Простой запуск bundled chromium без профилей
                logger.info("Launching bundled chromium for manifest capture")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(Path.cwd() / ".pw-temp-profile"),
                    headless=False,
                    args=[
                        "--autoplay-policy=no-user-gesture-required",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        # Убираем флаги автоматизации
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images",
                        "--disable-default-apps",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-hang-monitor",
                        "--disable-prompt-on-repost",
                        "--disable-sync",
                        "--disable-background-networking",
                        "--disable-client-side-phishing-detection",
                        "--disable-component-update",
                        "--disable-domain-reliability",
                        "--disable-features=AudioServiceOutOfProcess",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-features=WebRtcHideLocalIpsWithMdns",
                        "--disable-features=WebRtcUseMinMaxVEADimensions",
                        "--disable-logging",
                        "--disable-permissions-api",
                        "--disable-presentation-api",
                        "--disable-print-preview",
                        "--disable-speech-api",
                        "--hide-scrollbars",
                        "--mute-audio",
                        "--no-zygote",
                        "--use-mock-keychain",
                        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    ],
                )
                logger.info("Successfully launched bundled chromium")
                
                page = await context.new_page()
                
                # Маскируем автоматизацию
                await page.add_init_script("""
                    // Убираем webdriver флаг
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    // Маскируем автоматизацию
                    window.chrome = {
                        runtime: {},
                    };
                    
                    // Убираем automation флаги
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    // Маскируем permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                    
                    // Настройка для автоплей
                    Object.defineProperty(document, 'visibilityState', {get: () => 'visible'});
                    Object.defineProperty(document, 'hidden', {get: () => false});
                """)
                
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
        
        try:
            async with async_playwright() as p:
                # Простой запуск bundled chromium без профилей и куки
                logger.info("Launching bundled chromium for manual login")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(Path.cwd() / ".pw-temp-profile"),
                    headless=False,
                    args=[
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--autoplay-policy=no-user-gesture-required",
                        # Убираем флаги автоматизации
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images",
                        "--disable-default-apps",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-hang-monitor",
                        "--disable-prompt-on-repost",
                        "--disable-sync",
                        "--disable-background-networking",
                        "--disable-client-side-phishing-detection",
                        "--disable-component-update",
                        "--disable-domain-reliability",
                        "--disable-features=AudioServiceOutOfProcess",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-features=WebRtcHideLocalIpsWithMdns",
                        "--disable-features=WebRtcUseMinMaxVEADimensions",
                        "--disable-logging",
                        "--disable-permissions-api",
                        "--disable-presentation-api",
                        "--disable-print-preview",
                        "--disable-speech-api",
                        "--hide-scrollbars",
                        "--mute-audio",
                        "--no-zygote",
                        "--use-mock-keychain",
                        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    ],
                )
                logger.info("Successfully launched bundled chromium")
                
                page = await context.new_page()
                
                # Маскируем автоматизацию
                await page.add_init_script("""
                    // Убираем webdriver флаг
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    // Маскируем автоматизацию
                    window.chrome = {
                        runtime: {},
                    };
                    
                    // Убираем automation флаги
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    // Маскируем permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)
                
                # Переходим на страницу - пользователь может войти вручную
                logger.info("Opening page for manual login", extra={"url": url})
                await page.goto(url, wait_until="domcontentloaded")
                
                # Сохраняем HTML разметку для диагностики
                try:
                    html_content = await page.content()
                    html_file = Path.cwd() / "debug" / "page_debug.html"
                    html_file.write_text(html_content, encoding="utf-8")
                    logger.info("Saved page HTML for debugging", extra={"file": str(html_file)})
                except Exception as e:
                    logger.warning("Failed to save page HTML", extra={"error": str(e)})
                
                # Ждем появления видео на странице (означает успешный вход)
                logger.info("Waiting for video to appear on page (indicates successful login)...")
                try:
                    # Ждем появления видео элемента
                    await page.wait_for_selector("video", timeout=60000)  # 60 секунд на вход
                    logger.info("Video found on page - user is logged in")
                    
                    # Сохраняем HTML после появления видео
                    try:
                        html_content = await page.content()
                        html_file = Path.cwd() / "debug" / "page_with_video_debug.html"
                        html_file.write_text(html_content, encoding="utf-8")
                        logger.info("Saved page HTML with video for debugging", extra={"file": str(html_file)})
                    except Exception as e:
                        logger.warning("Failed to save page HTML with video", extra={"error": str(e)})
                    
                    # Пытаемся запустить воспроизведение
                    try:
                        await page.evaluate("""
                            const videos = document.querySelectorAll('video');
                            for (const video of videos) {
                                video.muted = true;
                                video.play().catch(() => {});
                            }
                        """)
                        logger.info("Attempted to start video playback")
                    except Exception as e:
                        logger.warning("Failed to start video playback", extra={"error": str(e)})
                        
                except Exception as e:
                    logger.warning("No video found on page", extra={"error": str(e)})
                    # Продолжаем в любом случае - возможно видео появится позже
                
                # Проверяем состояние видео перед попыткой скачивания
                try:
                    video_info = await page.evaluate("""
                        const videos = document.querySelectorAll('video');
                        const info = [];
                        for (const video of videos) {
                            info.push({
                                src: video.src,
                                currentSrc: video.currentSrc,
                                readyState: video.readyState,
                                networkState: video.networkState,
                                paused: video.paused,
                                ended: video.ended,
                                duration: video.duration,
                                currentTime: video.currentTime,
                                poster: video.poster
                            });
                        }
                        return info;
                    """)
                    logger.info("Video state before download attempt", extra={"video_info": video_info})
                except Exception as e:
                    logger.warning("Failed to get video state", extra={"error": str(e)})
                
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
                                        logger.info("Found download button", extra={"selector": sel, "frame": "iframe" if target_frame else "main"})
                                        await el.click(timeout=2000)
                                        return True
                                except Exception as e:
                                    logger.debug("Failed to click button", extra={"selector": sel, "error": str(e)})
                                    continue
                            return False
                        
                        # Клик в iframe или основной странице
                        clicked = False
                        if target_frame is not None:
                            logger.info("Trying to click download button in iframe")
                            clicked = await _click_in(target_frame)
                        if not clicked:
                            logger.info("Trying to click download button in main page")
                            clicked = await _click_in(page)
                        
                        # Попытка клика по ссылке скачивания
                        if target_frame is not None and not clicked:
                            try:
                                link = await target_frame.query_selector("a[download], a[href*='.mp4']")
                                if link:
                                    logger.info("Found download link in iframe")
                                    await link.click(timeout=2000)
                                    clicked = True
                            except Exception as e:
                                logger.debug("Failed to click download link", extra={"error": str(e)})
                        
                        if not clicked:
                            logger.info("No download button found, waiting for manual click")
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
