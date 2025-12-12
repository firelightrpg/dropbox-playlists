"""
Per-artist settings for characterization algorithms.
"""

import json
import os
from dataclasses import asdict, dataclass

from config import config


@dataclass
class ArtistSettings:
    """Settings for characterizing tracks from a specific artist."""

    artist_name: str

    # Rhythmic density thresholds
    rhythmic_threshold: float = 1.8  # Above this = Rhythmic
    ambient_threshold: float = 1.6  # Below this = Ambient

    # High-pass filter settings
    use_hpf: bool = False
    hpf_cutoff: float = 150.0

    # Minor 2nd detection sensitivity
    minor_2nd_sensitivity: float = 0.5  # Multiplier for Major 3rd comparison

    # Analysis duration settings
    max_duration: int = 180  # Max seconds to analyze
    start_offset: int = 30  # Where to start analysis

    # Optional notes for this artist's characteristics
    notes: str = ""


class ArtistSettingsManager:
    """Manage per-artist settings for characterization."""

    def __init__(self):
        self.settings_dir = config.SETTINGS_DIR
        os.makedirs(self.settings_dir, exist_ok=True)

    def get_settings(self, artist_name: str) -> ArtistSettings:
        """
        Load settings for an artist, or return defaults if not found.

        Args:
            artist_name: Name of the artist

        Returns:
            ArtistSettings for this artist
        """
        filepath = self._get_filepath(artist_name)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ArtistSettings(**data)

        # Return default settings
        return ArtistSettings(artist_name=artist_name)

    def save_settings(self, settings: ArtistSettings):
        """
        Save settings for an artist.

        Args:
            settings: ArtistSettings to save
        """
        filepath = self._get_filepath(settings.artist_name)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, indent=2, ensure_ascii=False)

    def _get_filepath(self, artist_name: str) -> str:
        """Get the filepath for an artist's settings."""
        # Sanitize artist name for filename
        safe_name = artist_name.replace("/", "-").replace("\\", "-")
        return os.path.join(self.settings_dir, f"{safe_name}.json")

    def list_artists(self) -> list[str]:
        """Get a list of all artists with saved settings."""
        if not os.path.exists(self.settings_dir):
            return []

        files = os.listdir(self.settings_dir)
        return [f.replace(".json", "") for f in files if f.endswith(".json")]


# Global instance
artist_settings_manager = ArtistSettingsManager()
