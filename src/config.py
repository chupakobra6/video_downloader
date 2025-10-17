"""Configuration and parameter validation."""

import logging
import tomllib
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Config:
    """Application configuration with validation."""

    def __init__(
        self,
        browser_profile: Optional[str] = None,
        output_root: Path = Path("downloads"),
        links_file: Path = Path("links.txt"),
        cookies_file: Optional[Path] = None,
    ):
        self.browser_profile = browser_profile
        self.output_root = output_root
        self.links_file = links_file
        self.cookies_file = cookies_file

    @classmethod
    def from_toml(cls, config_path: Path, project_root: Path) -> "Config":
        """Load configuration from TOML file."""
        try:
            with config_path.open("rb") as f:
                cfg: dict[str, Any] = tomllib.load(f)
        except Exception as e:
            logger.error(
                "Failed to load config",
                extra={"path": str(config_path), "error": str(e)},
            )
            raise ValueError(f"Invalid config file: {e}") from e

        browser_profile: Optional[str] = cfg.get("browser_profile")
        output_root: Path = Path(cfg.get("output_root", "downloads"))
        links_file: str = cfg.get("links_file", "links.txt")
        cookies_file_cfg: Optional[str] = cfg.get("cookies_file")

        # Handle paths
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
            browser_profile=browser_profile,
            output_root=output_root,
            links_file=links_path,
            cookies_file=cookies_file,
        )

    def validate(self) -> None:
        """Validate configuration."""
        if self.cookies_file and not self.cookies_file.exists():
            logger.warning(
                "Cookies file not found", extra={"path": str(self.cookies_file)}
            )

        logger.info(
            "Configuration loaded",
            extra={
                "profile": self.browser_profile,
                "output_root": str(self.output_root),
                "links_file": str(self.links_file),
                "cookies_file": str(self.cookies_file) if self.cookies_file else None,
            },
        )
