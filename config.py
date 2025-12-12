"""
Configuration settings for the playlist project.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Main configuration for the application."""

    # Debug mode - when True, files are preserved for algorithm tuning
    DEBUG_MODE: bool = True

    # Directory for persistent downloads during debug
    DOWNLOAD_DIR: str = "downloads"

    # Directory for per-artist characterization settings
    SETTINGS_DIR: str = "artist_settings"

    # Directory for JSON output
    JSON_DIR: str = "jsons"

    # Log file for tracking downloaded files
    DOWNLOAD_LOG: str = "downloads.log"

    # Whether to skip re-downloading existing files
    SKIP_EXISTING_DOWNLOADS: bool = True

    # Whether to re-analyze existing tracks (useful when tuning)
    FORCE_REANALYSIS: bool = True

    def __post_init__(self):
        """Create necessary directories."""
        if self.DEBUG_MODE:
            os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
            os.makedirs(self.SETTINGS_DIR, exist_ok=True)
        os.makedirs(self.JSON_DIR, exist_ok=True)


# Global config instance
config = Config()
