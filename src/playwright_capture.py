"""Video capture via Playwright for DRM and non-standard cases."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Tuple
from urllib.parse import urljoin

import requests

if TYPE_CHECKING:
    from playwright.async_api import async_playwright
else:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        async_playwright = None

logger = logging.getLogger(__name__)


class PlaywrightCapture:
    """Video capture via browser using Playwright."""

    def __init__(self) -> None:
        self.playwright_available = async_playwright is not None
        if not self.playwright_available:
            logger.warning("Playwright not available - browser capture disabled")

    def _get_chrome_like_base(self, browser: str) -> Optional[Path]:
        """Get base path to browser profiles."""
        base: Optional[Path] = None
        match sys.platform:
            case "darwin":
                match browser:
                    case "chrome":
                        base = Path.home() / "Library/Application Support/Google/Chrome"
                    case "brave":
                        base = (
                            Path.home()
                            / "Library/Application Support/BraveSoftware/Brave-Browser"
                        )
                    case "edge":
                        base = (
                            Path.home() / "Library/Application Support/Microsoft Edge"
                        )
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

    def _http_get_text(
        self, url: str, headers: Optional[dict[str, str]], timeout_sec: int = 30
    ) -> Optional[str]:
        """Get text via HTTP."""
        try:
            resp = requests.get(url, headers=headers or {}, timeout=timeout_sec)
            if resp.status_code >= 400:
                return None
            return str(resp.text)
        except Exception as e:
            logger.exception("HTTP GET failed", extra={"url": url, "error": str(e)})
            return None

    def detect_drm_in_m3u8(
        self, manifest_url: str, headers: Optional[dict[str, str]]
    ) -> Tuple[bool, Optional[str]]:
        """Detect DRM in HLS manifests."""
        root = self._http_get_text(manifest_url, headers)
        if not root:
            return False, None

        text = root
        lower = text.lower()

        # Check for master manifest
        if "#ext-x-session-key" in lower and "sample-aes" in lower:
            return True, "SAMPLE-AES(session)"
        if "com.apple.fps" in lower or "fairplay" in lower:
            return True, "FairPlay"
        if "com.widevine.alpha" in lower or "widevine" in lower:
            return True, "Widevine"

        # Search for variant URL to check
        variant_url: Optional[str] = None
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(".m3u8"):
                variant_url = urljoin(manifest_url, line)
                break

        if not variant_url:
            # Single-level manifest
            if "#ext-x-key" in lower:
                if "sample-aes" in lower:
                    return True, "SAMPLE-AES"
                if "aes-128" in lower:
                    return False, "AES-128"
            return False, None

        # Check variant manifest
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
        """Capture stream manifest via browser."""
        if not self.playwright_available:
            return None

        logger.info(
            "START capture_stream_manifest",
            extra={"url": page_url, "timeout": wait_timeout_sec},
        )

        try:
            async with async_playwright() as p:
                # Simple launch of bundled chromium without profiles
                logger.info("Launching bundled chromium for manifest capture")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(Path.cwd() / ".pw-temp-profile"),
                    headless=False,
                    args=[
                        "--autoplay-policy=no-user-gesture-required",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        # Remove automation flags
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
                        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36",
                    ],
                )
                logger.info("Successfully launched bundled chromium")

                page = await context.new_page()

                # Mask automation
                await page.add_init_script(
                    """
                    // Remove webdriver flag
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });

                    // Mask automation
                    window.chrome = {
                        runtime: {},
                    };

                    // Remove automation flags
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });

                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });

                    // Mask permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );

                    // Setup for autoplay
                    Object.defineProperty(document, 'visibilityState', {
                        get: () => 'visible'
                    });
                    Object.defineProperty(document, 'hidden', {get: () => false});
                """
                )

                # Capture manifest
                found: asyncio.Future[
                    Tuple[str, dict[str, str]]
                ] = asyncio.get_event_loop().create_future()

                def _maybe_set(req_url: str, headers: dict[str, str]) -> None:
                    try:
                        if any(s in req_url for s in [".m3u8", ".mpd", "format=m3u8"]):
                            if not found.done():
                                found.set_result((req_url, headers))
                    except Exception:
                        pass

                page.on(
                    "request", lambda request: _maybe_set(request.url, request.headers)
                )

                async def on_response(response: Any) -> None:
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

                # Get page title
                page_title: Optional[str] = None
                try:
                    page_title = await page.title()
                except Exception:
                    pass

                # Attempt to start playback
                selectors = [
                    "video",
                    "jugru-video video",
                    "button[aria-label='Play']",
                    "[data-testid='play'], .play, .video-play",
                ]
                for sel in selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            await el.click(timeout=2000)
                    except Exception:
                        continue

                # Programmatic video start
                try:
                    await page.evaluate(
                        """
                        const v = document.querySelector('video');
                        if (v) { v.muted = true; v.play().catch(()=>{}); }
                    """
                    )
                except Exception:
                    pass

                try:
                    logger.info(
                        "Waiting for video manifest",
                        extra={"timeout_sec": wait_timeout_sec},
                    )
                    manifest_url, req_headers = await asyncio.wait_for(
                        found, timeout=wait_timeout_sec
                    )
                    await context.close()
                    logger.info(
                        "DONE capture_stream_manifest",
                        extra={"manifest_url": manifest_url},
                    )
                    return manifest_url, req_headers, page_title
                except asyncio.TimeoutError:
                    await context.close()
                    logger.info(
                        "FAIL capture_stream_manifest - timeout",
                        extra={"url": page_url},
                    )
                    return None

        except Exception as e:
            logger.exception(
                "FAIL capture_stream_manifest", extra={"url": page_url, "error": str(e)}
            )
            return None

    async def attempt_browser_download(
        self,
        url: str,
        browser: str,
        resolved_profile: Optional[str],
        output_dir: Path,
        wait_timeout_sec: int = 180,
    ) -> Optional[Path]:
        """Attempt download via browser."""
        if not self.playwright_available:
            return None

        logger.info(
            "START attempt_browser_download",
            extra={"url": url, "timeout": wait_timeout_sec},
        )

        try:
            async with async_playwright() as p:
                # Simple launch of bundled chromium without profiles and cookies
                logger.info("Launching bundled chromium for manual login")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(Path.cwd() / ".pw-temp-profile"),
                    headless=False,
                    args=[
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--autoplay-policy=no-user-gesture-required",
                        # Remove automation flags
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
                        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36",
                    ],
                )
                logger.info("Successfully launched bundled chromium")

                page = await context.new_page()

                # Mask automation
                await page.add_init_script(
                    """
                    // Remove webdriver flag
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });

                    // Mask automation
                    window.chrome = {
                        runtime: {},
                    };

                    // Remove automation flags
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });

                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });

                    // Mask permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """
                )

                # Navigate to page - user can log in manually
                logger.info("Opening page for manual login", extra={"url": url})
                await page.goto(url, wait_until="domcontentloaded")

                # Save HTML markup for diagnostics
                try:
                    html_content = await page.content()
                    html_file = Path.cwd() / "debug" / "page_debug.html"
                    html_file.write_text(html_content, encoding="utf-8")
                    logger.info(
                        "Saved page HTML for debugging", extra={"file": str(html_file)}
                    )
                except Exception as e:
                    logger.warning("Failed to save page HTML", extra={"error": str(e)})

                # Wait for video to appear on page (indicates successful login)
                logger.info(
                    "Waiting for video to appear on page "
                    "(indicates successful login)..."
                )
                try:
                    # Wait for video element to appear
                    await page.wait_for_selector(
                        "video", timeout=60000
                    )  # 60 seconds for login
                    logger.info("Video found on page - user is logged in")

                    # Save HTML after video appears
                    try:
                        html_content = await page.content()
                        html_file = Path.cwd() / "debug" / "page_with_video_debug.html"
                        html_file.write_text(html_content, encoding="utf-8")
                        logger.info(
                            "Saved page HTML with video for debugging",
                            extra={"file": str(html_file)},
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to save page HTML with video",
                            extra={"error": str(e)},
                        )

                    # Attempt to start playback
                    try:
                        await page.evaluate(
                            """
                            const videos = document.querySelectorAll('video');
                            for (const video of videos) {
                                video.muted = true;
                                video.play().catch(() => {});
                            }
                        """
                        )
                        logger.info("Attempted to start video playback")
                    except Exception as e:
                        logger.warning(
                            "Failed to start video playback", extra={"error": str(e)}
                        )

                except Exception as e:
                    logger.warning("No video found on page", extra={"error": str(e)})
                    # Continue anyway - video might appear later

                # Check video state before download attempt
                try:
                    video_info = await page.evaluate(
                        """
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
                    """
                    )
                    logger.info(
                        "Video state before download attempt",
                        extra={"video_info": video_info},
                    )
                except Exception as e:
                    logger.warning("Failed to get video state", extra={"error": str(e)})

                logger.info(
                    "Waiting for browser download",
                    extra={"timeout_sec": wait_timeout_sec},
                )

                try:
                    async with page.expect_download(
                        timeout=wait_timeout_sec * 1000
                    ) as dl_info:
                        # Search for Kinescope iframe
                        target_frame = None
                        try:
                            for fr in page.frames:
                                if "kinescope.io" in (fr.url or ""):
                                    target_frame = fr
                                    break
                        except Exception:
                            target_frame = None

                        # Selectors for download buttons
                        candidates = [
                            "button[aria-label*='Download']",
                            "button[aria-label*='download']",
                            "button[aria-label*='Download' i]",
                            "button:has-text('Download')",
                            "button:has-text('Download')",
                            "[data-testid='downloadsButton']",
                            "[data-testid='downloadButton']",
                            ".kin-pl-downloadsButton",
                            "[class*='downloads'] button",
                        ]

                        async def _click_in(frame_obj: Any) -> bool:
                            for sel in candidates:
                                try:
                                    el = await frame_obj.query_selector(sel)
                                    if el:
                                        logger.info(
                                            "Found download button",
                                            extra={
                                                "selector": sel,
                                                "frame": "iframe"
                                                if target_frame
                                                else "main",
                                            },
                                        )
                                        await el.click(timeout=2000)
                                        return True
                                except Exception as e:
                                    logger.debug(
                                        "Failed to click button",
                                        extra={"selector": sel, "error": str(e)},
                                    )
                                    continue
                            return False

                        # Click in iframe or main page
                        clicked = False
                        if target_frame is not None:
                            logger.info("Trying to click download button in iframe")
                            clicked = await _click_in(target_frame)
                        if not clicked:
                            logger.info("Trying to click download button in main page")
                            clicked = await _click_in(page)

                        # Attempt to click download link
                        if target_frame is not None and not clicked:
                            try:
                                link = await target_frame.query_selector(
                                    "a[download], a[href*='.mp4']"
                                )
                                if link:
                                    logger.info("Found download link in iframe")
                                    await link.click(timeout=2000)
                                    clicked = True
                            except Exception as e:
                                logger.debug(
                                    "Failed to click download link",
                                    extra={"error": str(e)},
                                )

                        if not clicked:
                            logger.info(
                                "No download button found, waiting for manual click"
                            )
                            # Give user time for manual click
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

                    logger.info(
                        "DONE attempt_browser_download", extra={"file": str(target)}
                    )
                    return target

                except Exception as e:
                    await context.close()
                    logger.info(
                        "FAIL attempt_browser_download - no download triggered",
                        extra={"url": url, "error": str(e)},
                    )
                    return None

        except Exception as e:
            logger.exception(
                "FAIL attempt_browser_download", extra={"url": url, "error": str(e)}
            )
            return None
