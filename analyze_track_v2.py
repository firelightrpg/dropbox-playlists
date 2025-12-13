"""
Enhanced audio analysis using librosa with more robust features.

This approach extracts multiple features and combines them for more reliable
categorization across different artists/genres.

Categories:
- Dark: ambient, minor/tense feel
- Light: ambient, major/peaceful feel
- Combat: driving, intense
- Theme: driving, triumphant/heroic
"""

from dataclasses import dataclass
from typing import Literal

import librosa
import numpy as np

MoodCategory = Literal["Dark", "Light", "Combat", "Theme"]


@dataclass
class AudioFeatures:
    """Extracted audio features for mood classification."""

    # Energy/Intensity features
    rms_energy: float  # Root mean square energy
    spectral_centroid: float  # Brightness (higher = brighter)
    spectral_rolloff: float  # Frequency below which 85% of energy lies

    # Rhythmic features
    tempo: float  # BPM
    onset_strength: float  # Attack/percussive strength
    beat_strength: float  # How strong/regular the beat is

    # Harmonic features
    mode: float  # Major (1) vs Minor (0) likelihood
    harmonic_ratio: float  # Harmonic vs percussive content
    dissonance: float  # Harmonic tension/dissonance

    # Dynamics
    dynamic_range: float  # Difference between loud and quiet

    def to_dict(self) -> dict:
        return {
            "rms_energy": self.rms_energy,
            "spectral_centroid": self.spectral_centroid,
            "spectral_rolloff": self.spectral_rolloff,
            "tempo": self.tempo,
            "onset_strength": self.onset_strength,
            "beat_strength": self.beat_strength,
            "mode": self.mode,
            "harmonic_ratio": self.harmonic_ratio,
            "dissonance": self.dissonance,
            "dynamic_range": self.dynamic_range,
        }


def extract_features(
    file_path: str, duration: float = 120, offset: float = 30
) -> AudioFeatures:
    """
    Extract comprehensive audio features from a track.

    Args:
        file_path: Path to audio file
        duration: Max seconds to analyze
        offset: Where to start analysis (skip intros)

    Returns:
        AudioFeatures dataclass with all extracted features
    """
    # Load audio
    y, sr = librosa.load(file_path, sr=22050, duration=duration, offset=offset)

    # Harmonic-percussive separation
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # === ENERGY/INTENSITY ===

    # RMS energy (overall loudness)
    rms = librosa.feature.rms(y=y)[0]
    rms_energy = float(np.mean(rms))

    # Spectral centroid (brightness)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_centroid = float(np.mean(centroid))

    # Spectral rolloff
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    spectral_rolloff = float(np.mean(rolloff))

    # === RHYTHMIC ===

    # Tempo
    tempo, beat_frames = librosa.beat.beat_track(y=y_percussive, sr=sr)
    tempo = float(tempo) if np.isscalar(tempo) else float(tempo[0])

    # Onset strength
    onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr)
    onset_strength = float(np.mean(onset_env))

    # Beat strength (regularity of beat)
    if len(beat_frames) > 1:
        beat_intervals = np.diff(librosa.frames_to_time(beat_frames, sr=sr))
        beat_strength = float(
            1.0 / (np.std(beat_intervals) + 0.01)
        )  # Lower variance = stronger beat
    else:
        beat_strength = 0.0

    # === HARMONIC ===

    # Chroma for mode detection
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
    chroma_sum = chroma.sum(axis=1)
    root = np.argmax(chroma_sum)

    # Major vs minor based on 3rd
    major_third = chroma[(root + 4) % 12].sum()
    minor_third = chroma[(root + 3) % 12].sum()
    mode = float(major_third / (major_third + minor_third + 0.001))

    # Harmonic ratio
    harmonic_energy = np.sum(y_harmonic**2)
    percussive_energy = np.sum(y_percussive**2)
    harmonic_ratio = float(
        harmonic_energy / (harmonic_energy + percussive_energy + 0.001)
    )

    # Dissonance (simplified - using spectral contrast variance)
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    dissonance = float(np.std(contrast))

    # === DYNAMICS ===

    # Dynamic range
    rms_db = librosa.power_to_db(rms**2)
    dynamic_range = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 5))

    return AudioFeatures(
        rms_energy=rms_energy,
        spectral_centroid=spectral_centroid,
        spectral_rolloff=spectral_rolloff,
        tempo=tempo,
        onset_strength=onset_strength,
        beat_strength=beat_strength,
        mode=mode,
        harmonic_ratio=harmonic_ratio,
        dissonance=dissonance,
        dynamic_range=dynamic_range,
    )


def classify_mood(features: AudioFeatures) -> tuple[MoodCategory, dict]:
    """
    Classify mood based on extracted features.

    Uses a two-axis model:
    - Intensity (ambient vs driving): based on onset_strength, tempo, rms_energy
    - Valence (dark vs light): based on mode, dissonance, spectral_centroid

    Returns:
        Tuple of (category, debug_info)
    """
    # Calculate intensity score (0 = ambient, 1 = driving)
    # Normalize each feature to roughly 0-1 range
    tempo_score = min(1.0, features.tempo / 140)  # 140 BPM = max intensity
    onset_score = min(1.0, features.onset_strength / 3.0)
    energy_score = min(1.0, features.rms_energy / 0.1)

    intensity = tempo_score * 0.3 + onset_score * 0.5 + energy_score * 0.2

    # Calculate valence score (0 = dark/tense, 1 = light/triumphant)
    mode_score = features.mode  # Already 0-1
    brightness_score = min(1.0, features.spectral_centroid / 3000)
    consonance_score = 1.0 - min(1.0, features.dissonance / 30)

    valence = mode_score * 0.5 + brightness_score * 0.25 + consonance_score * 0.25

    debug_info = {
        "intensity": intensity,
        "valence": valence,
        "tempo_score": tempo_score,
        "onset_score": onset_score,
        "energy_score": energy_score,
        "mode_score": mode_score,
        "brightness_score": brightness_score,
        "consonance_score": consonance_score,
        "features": features.to_dict(),
    }

    # Classify based on quadrant
    intensity_threshold = 0.45
    valence_threshold = 0.5

    if intensity > intensity_threshold:
        # Driving
        if valence > valence_threshold:
            return "Theme", debug_info
        else:
            return "Combat", debug_info
    else:
        # Ambient
        if valence > valence_threshold:
            return "Light", debug_info
        else:
            return "Dark", debug_info


def analyze_track_v2(file_path: str, artist_name: str = None) -> dict:
    """
    Analyze a track using enhanced feature extraction.

    Args:
        file_path: Path to audio file
        artist_name: Optional artist name for settings lookup

    Returns:
        Dict with mood, features, and debug info
    """
    features = extract_features(file_path)
    mood, debug_info = classify_mood(features)

    return {
        "mood": mood,
        "intensity": debug_info["intensity"],
        "valence": debug_info["valence"],
        "features": debug_info["features"],
        "debug": debug_info,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_track_v2.py <audio_file>")
        sys.exit(1)

    result = analyze_track_v2(sys.argv[1])

    print(f"\nMood: {result['mood']}")
    print(f"Intensity: {result['intensity']:.2f} (0=ambient, 1=driving)")
    print(f"Valence: {result['valence']:.2f} (0=dark, 1=light)")
    print(f"\nRaw features:")
    for k, v in result["features"].items():
        print(f"  {k}: {v:.4f}")
