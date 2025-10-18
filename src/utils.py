"""Utility functions."""

import logging
from pathlib import Path
from typing import List
from urllib.parse import urlparse


def configure_logging(level: int = logging.INFO) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def read_links_file(file_path: Path) -> List[str]:
    """Read URLs from file."""
    if not file_path.exists():
        return []

    urls: List[str] = []
    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    except Exception as e:
        logging.getLogger(__name__).exception(
            "Failed to read links file", extra={"file": str(file_path), "error": str(e)}
        )

    return urls


def validate_urls(urls: List[str]) -> List[str]:
    """Validate URLs."""
    valid_urls: List[str] = []
    for url in urls:
        try:
            parsed = urlparse(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                valid_urls.append(url)
            else:
                logging.getLogger(__name__).warning(
                    "Invalid URL format", extra={"url": url}
                )
        except Exception as e:
            logging.getLogger(__name__).warning(
                "URL validation failed", extra={"url": url, "error": str(e)}
            )

    return valid_urls
