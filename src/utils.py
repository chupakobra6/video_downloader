"""Утилиты для работы с файлами и URL."""

import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


def read_links_file(path: Path) -> list[str]:
    """Прочитать файл с ссылками."""
    if not path.exists():
        logger.info("Links file not found, creating template", extra={"path": str(path)})
        path.write_text("# Add your URLs here, one per line\n", encoding="utf-8")
        return []
    
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def configure_logging(level: int = logging.INFO) -> None:
    """Настроить логирование."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def validate_urls(urls: Iterable[str]) -> list[str]:
    """Валидировать и очистить список URL."""
    valid_urls = []
    for url in urls:
        url = url.strip()
        if url and (url.startswith("http://") or url.startswith("https://")):
            valid_urls.append(url)
        elif url:
            logger.warning("Invalid URL format", extra={"url": url})
    return valid_urls
