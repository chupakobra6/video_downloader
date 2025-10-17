"""Конфигурация и валидация параметров."""

import logging
from pathlib import Path
from typing import Optional

import tomllib

logger = logging.getLogger(__name__)


class Config:
    """Конфигурация приложения с валидацией."""
    
    def __init__(
        self,
        browser: str = "chrome",
        browser_profile: Optional[str] = None,
        output_root: Path = Path("downloads"),
        links_file: Path = Path("links.txt"),
        cookies_file: Optional[Path] = None,
    ):
        self.browser = browser
        self.browser_profile = browser_profile
        self.output_root = output_root
        self.links_file = links_file
        self.cookies_file = cookies_file
        
    @classmethod
    def from_toml(cls, config_path: Path, project_root: Path) -> "Config":
        """Загрузить конфигурацию из TOML файла."""
        try:
            with config_path.open("rb") as f:
                cfg = tomllib.load(f)
        except Exception as e:
            logger.error("Failed to load config", extra={"path": str(config_path), "error": str(e)})
            raise ValueError(f"Invalid config file: {e}") from e
            
        browser = cfg.get("browser", "chrome")
        browser_profile = cfg.get("browser_profile")
        output_root = Path(cfg.get("output_root", "downloads"))
        links_file = cfg.get("links_file", "links.txt")
        cookies_file_cfg = cfg.get("cookies_file")
        
        # Обработка путей
        cookies_file: Optional[Path] = None
        if cookies_file_cfg:
            cookies_file = (
                Path(cookies_file_cfg)
                if Path(cookies_file_cfg).is_absolute()
                else project_root / cookies_file_cfg
            )
            
        links_path = (
            project_root / links_file
            if not Path(links_file).is_absolute()
            else Path(links_file)
        )
        
        return cls(
            browser=browser,
            browser_profile=browser_profile,
            output_root=output_root,
            links_file=links_path,
            cookies_file=cookies_file,
        )
    
    def validate(self) -> None:
        """Валидировать конфигурацию."""
        valid_browsers = {"chrome", "brave", "edge", "chromium", "safari"}
        if self.browser not in valid_browsers:
            raise ValueError(f"Invalid browser: {self.browser}. Must be one of {valid_browsers}")
            
        if self.cookies_file and not self.cookies_file.exists():
            logger.warning("Cookies file not found", extra={"path": str(self.cookies_file)})
            
        logger.info(
            "Configuration loaded",
            extra={
                "browser": self.browser,
                "profile": self.browser_profile,
                "output_root": str(self.output_root),
                "links_file": str(self.links_file),
                "cookies_file": str(self.cookies_file) if self.cookies_file else None,
            },
        )
