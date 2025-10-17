"""CLI interface for video_downloader."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import Config
from .downloader import VideoDownloader
from .utils import configure_logging, read_links_file, validate_urls

logger = logging.getLogger(__name__)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Download authenticated videos with yt-dlp using your browser cookies. "
            "Outputs to downloads/<domain>/"
        )
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help=(
            "List of URLs and/or paths to text files with URLs (one per line). "
            "Files are detected by existing paths. If not provided, "
            "uses links_file from config."
        ),
    )
    parser.add_argument(
        "--browser",
        default="chrome",
        choices=["chrome", "brave", "edge", "chromium", "safari"],
        help="Browser to read cookies from (must be logged in).",
    )
    parser.add_argument(
        "--browser-profile",
        default=None,
        help="Optional browser profile name (e.g. 'Default', 'Profile 1').",
    )
    parser.add_argument(
        "--output-root",
        default="downloads",
        help="Root output directory (default: downloads)",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to config file (default: config.toml)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args(argv)


def resolve_urls(inputs: list[str]) -> list[str]:
    """Resolve input data to a list of URLs."""
    urls: list[str] = []
    for item in inputs:
        path = Path(item)
        if path.exists() and path.is_file():
            file_urls = read_links_file(path)
            urls.extend(file_urls)
        else:
            urls.append(item)
    return urls


def main(argv: Optional[list[str]] = None) -> None:
    """Main CLI function."""
    args = parse_args(sys.argv[1:] if argv is None else argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(log_level)

    logger.info("START cli_main")

    try:
        # Load configuration
        config_path = Path(args.config)
        project_root = Path.cwd()

        if config_path.exists():
            config = Config.from_toml(config_path, project_root)
        else:
            logger.info(
                "Config file not found, using defaults",
                extra={"path": str(config_path)},
            )
            config = Config(
                browser=args.browser,
                browser_profile=args.browser_profile,
                output_root=Path(args.output_root),
            )

        # Validate configuration
        config.validate()

        # Resolve URLs
        if args.inputs:
            urls = resolve_urls(args.inputs)
        else:
            # Use links file from configuration
            urls = read_links_file(config.links_file)

        valid_urls = validate_urls(urls)

        if not valid_urls:
            logger.info("No valid URLs to download")
            return

        logger.info(
            "Starting downloads",
            extra={
                "browser": config.browser,
                "profile": config.browser_profile,
                "output_root": str(config.output_root),
                "count": len(valid_urls),
            },
        )

        # Download
        downloader = VideoDownloader(
            browser=config.browser,
            browser_profile=config.browser_profile,
            cookies_file=config.cookies_file,
        )

        downloader.download_videos(valid_urls, config.output_root)

        logger.info("DONE cli_main")

    except Exception as e:
        logger.exception("FAIL cli_main", extra={"error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
