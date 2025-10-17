"""File management and artifact cleanup."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileManager:
    """File manager for yt-dlp artifact cleanup."""
    
    def _get_partial_paths(self, final_path: Path) -> list[Path]:
        """Get possible paths to partial files."""
        candidates: list[Path] = []
        try:
            # Standard yt-dlp partial file markers
            candidates.append(final_path.with_suffix(final_path.suffix + ".part"))
            candidates.append(final_path.with_suffix(final_path.suffix + ".ytdl"))
            candidates.append(final_path.with_suffix(".part"))
        except Exception:
            return []
        return candidates
    
    def _remove_partials(self, final_path: Path) -> None:
        """Remove partial files."""
        for partial_path in self._get_partial_paths(final_path):
            try:
                if partial_path.exists():
                    partial_path.unlink(missing_ok=True)
                    logger.debug("Removed partial file", extra={"path": str(partial_path)})
            except Exception as e:
                logger.warning("Failed to remove partial file", extra={"path": str(partial_path), "error": str(e)})
    
    def _cleanup_artifacts(self, final_path: Path) -> None:
        """Clean up yt-dlp artifacts around final file."""
        try:
            directory = final_path.parent
            prefix = final_path.name + ".part"
            
            # Remove files with .part prefix
            for child in directory.iterdir():
                name = child.name
                if name == final_path.name:
                    continue
                if name.startswith(prefix):
                    try:
                        child.unlink(missing_ok=True)
                        logger.debug("Removed artifact", extra={"path": str(child)})
                    except Exception as e:
                        logger.warning("Failed to remove artifact", extra={"path": str(child), "error": str(e)})
            
            # Remove .ytdl sidecar file
            sidecar = final_path.with_suffix(final_path.suffix + ".ytdl")
            try:
                if sidecar.exists():
                    sidecar.unlink(missing_ok=True)
                    logger.debug("Removed sidecar file", extra={"path": str(sidecar)})
            except Exception as e:
                logger.warning("Failed to remove sidecar file", extra={"path": str(sidecar), "error": str(e)})
                
        except Exception as e:
            logger.exception("Artifacts cleanup failed", extra={"final_path": str(final_path), "error": str(e)})
    
    def sweep_leftovers(self, directory: Path) -> None:
        """Clean up remaining artifacts in directory."""
        try:
            for child in directory.iterdir():
                name = child.name
                
                # Handle .ytdl sidecar files
                if name.endswith(".ytdl"):
                    base = name[:-5]
                    if (directory / base).exists():
                        try:
                            child.unlink(missing_ok=True)
                            logger.debug("Swept sidecar file", extra={"path": str(child)})
                        except Exception as e:
                            logger.warning("Failed to sweep sidecar file", extra={"path": str(child), "error": str(e)})
                    continue
                
                # Handle .part partial files
                if ".part" in name:
                    base = name.split(".part", 1)[0]
                    if (directory / base).exists():
                        try:
                            child.unlink(missing_ok=True)
                            logger.debug("Swept partial file", extra={"path": str(child)})
                        except Exception as e:
                            logger.warning("Failed to sweep partial file", extra={"path": str(child), "error": str(e)})
                            
        except Exception as e:
            logger.exception("Leftovers sweep failed", extra={"directory": str(directory), "error": str(e)})
    
    def should_skip_download(self, expected_path: Path) -> bool:
        """Check if download should be skipped (file already exists)."""
        if not expected_path.exists():
            return False
            
        # Check for partial files
        has_partials = any(p.exists() for p in self._get_partial_paths(expected_path))
        if has_partials:
            logger.info("Found partial files, will resume download", extra={"file": str(expected_path)})
            return False
            
        # File exists and no partial files - skip
        logger.info("File already exists, skipping", extra={"file": str(expected_path)})
        self._cleanup_artifacts(expected_path)
        return True
