"""Browser profile and cookie management."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BrowserProfileManager:
    """Browser profile manager for cookie extraction."""
    
    def __init__(self, browser: str):
        self.browser = browser
        self._base_path = self._get_chrome_like_base()
        
    def _get_chrome_like_base(self) -> Optional[Path]:
        """Get base path to browser profiles."""
        base: Optional[Path] = None
        match sys.platform:
            case "darwin":
                match self.browser:
                    case "chrome":
                        base = Path.home() / "Library/Application Support/Google/Chrome"
                    case "brave":
                        base = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"
                    case "edge":
                        base = Path.home() / "Library/Application Support/Microsoft Edge"
                    case "chromium":
                        base = Path.home() / "Library/Application Support/Chromium"
            case "linux" | "linux2":
                match self.browser:
                    case "chrome":
                        base = Path.home() / ".config/google-chrome"
                    case "brave":
                        base = Path.home() / ".config/BraveSoftware/Brave-Browser"
                    case "edge":
                        base = Path.home() / ".config/microsoft-edge"
                    case "chromium":
                        base = Path.home() / ".config/chromium"
        return base if base and base.exists() else None
    
    def _has_cookies(self, dir_name: str) -> bool:
        """Check for cookies in profile."""
        if not self._base_path:
            return False
        profile_dir = self._base_path / dir_name
        if not profile_dir.exists():
            logger.debug("Profile directory does not exist", extra={"profile": dir_name, "path": str(profile_dir)})
            return False
        
        cookies_path1 = profile_dir / "Cookies"
        cookies_path2 = profile_dir / "Network" / "Cookies"
        has_cookies = cookies_path1.exists() or cookies_path2.exists()
        
        logger.debug(
            "Cookie check result",
            extra={
                "profile": dir_name,
                "path": str(profile_dir),
                "cookies1": str(cookies_path1),
                "cookies1_exists": cookies_path1.exists(),
                "cookies2": str(cookies_path2),
                "cookies2_exists": cookies_path2.exists(),
                "has_cookies": has_cookies,
            },
        )
        
        return has_cookies
    
    def _map_display_name_to_profile_dir(self, display_name: str) -> Optional[str]:
        """Map display name to profile directory."""
        if not self._base_path:
            return None
            
        try:
            local_state_path = self._base_path / "Local State"
            if not local_state_path.exists():
                return None
                
            data = json.loads(local_state_path.read_text(encoding="utf-8"))
            info_cache = (data or {}).get("profile", {}).get("info_cache", {})
            target = display_name.strip().casefold()
            
            for dir_name, meta in info_cache.items():
                try:
                    if not isinstance(meta, dict):
                        continue
                    name = str(meta.get("name", "")).strip()
                    gaia = str(meta.get("gaia_name", "")).strip()
                    
                    if name and name.strip().casefold() == target:
                        return dir_name
                    if gaia and gaia.strip().casefold() == target:
                        return dir_name
                except Exception:
                    continue
                    
            # Log available profiles to help user
            if info_cache:
                candidates = [
                    f"{dir_name} -> name='{meta.get('name', '')}', gaia='{meta.get('gaia_name', '')}'"
                    for dir_name, meta in info_cache.items()
                    if isinstance(meta, dict)
                ]
                logger.info("Available browser profiles", extra={"candidates": "; ".join(candidates)})
                
        except Exception as e:
            logger.exception("Failed to map profile name", extra={"display_name": display_name, "error": str(e)})
            
        return None
    
    def _get_display_name_for_dir(self, dir_name: str) -> Optional[str]:
        """Get display name for profile directory."""
        if not self._base_path:
            return None
            
        try:
            local_state_path = self._base_path / "Local State"
            if not local_state_path.exists():
                return None
                
            data = json.loads(local_state_path.read_text(encoding="utf-8"))
            info_cache = (data or {}).get("profile", {}).get("info_cache", {})
            meta = info_cache.get(dir_name)
            
            if isinstance(meta, dict):
                name = str(meta.get("name") or "").strip() or None
                if name:
                    return name
                gaia = str(meta.get("gaia_name") or "").strip() or None
                return gaia
                
        except Exception as e:
            logger.exception("Failed to get display name", extra={"dir_name": dir_name, "error": str(e)})
            
        return None
    
    def find_profile_name(self, requested_profile: Optional[str]) -> Optional[str]:
        """Find profile name for use."""
        logger.info(
            "Finding profile name",
            extra={
                "browser": self.browser,
                "requested_profile": requested_profile,
                "base_path": str(self._base_path) if self._base_path else None,
            },
        )
        
        if not self._base_path:
            logger.info("No base path found, returning requested profile", extra={"profile": requested_profile})
            return requested_profile
            
        # If profile specified, try direct path, then name mapping
        if requested_profile:
            if self._has_cookies(requested_profile):
                logger.info("Found direct profile match", extra={"profile": requested_profile})
                return requested_profile
                
            mapped = self._map_display_name_to_profile_dir(requested_profile)
            if mapped and self._has_cookies(mapped):
                logger.info("Found mapped profile", extra={"requested": requested_profile, "mapped": mapped})
                return mapped
        
        # Fallback to standard profiles
        for candidate in ["Default", "Profile 1", "Profile 2", "Profile 3"]:
            if self._has_cookies(candidate):
                logger.info("Found fallback profile", extra={"profile": candidate})
                return candidate
                
        logger.warning("No profile found with cookies", extra={"browser": self.browser})
        return None
    
    def get_profile_info(self, profile_name: Optional[str]) -> dict:
        """Get profile information."""
        if not profile_name:
            return {"name": "default", "display_name": None}
            
        display_name = self._get_display_name_for_dir(profile_name)
        return {
            "name": profile_name,
            "display_name": display_name,
        }
