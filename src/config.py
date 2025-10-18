"""Configuration and parameter validation."""

import logging
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Config:
    """Application configuration with validation."""

    def __init__(
        self,
        output_root: Path = Path("downloads"),
        links_file: Path = Path("links.txt"),
    ):
        self.output_root = output_root
        self.links_file = links_file

    @classmethod
    def from_toml(cls, config_path: Path, project_root: Path) -> "Config":
        """Load configuration from TOML file."""
        try:
            with config_path.open("rb") as f:
                cfg: dict[str, Any] = tomllib.load(f)
        except Exception as e:
            logger.exception(
                "Failed to load config",
                extra={"path": str(config_path), "error": str(e)},
            )
            raise ValueError(f"Invalid config file: {e}") from e

        output_root: Path = Path(cfg.get("output_root", "downloads"))
        links_file: str = cfg.get("links_file", "links.txt")

        links_path = (
            project_root / links_file
            if not Path(links_file).is_absolute()
            else Path(links_file)
        )

        return cls(
            output_root=output_root,
            links_file=links_path,
        )

    def validate(self) -> None:
        """Validate configuration."""
        logger.info(
            "Configuration loaded",
            extra={
                "output_root": str(self.output_root),
                "links_file": str(self.links_file),
            },
        )
