"""
Analyze audio for mood
"""

import librosa
import numpy as np
from librosa import feature
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from scipy.signal import butter, filtfilt

HPF = False  # Toggle high-pass filtering


def get_artists_from_mp3_metadata(mp3_filepath: str) -> list[str]:
    """
    Extract contributing artists from an MP3 file.

    Args:
        mp3_filepath:

    Returns:
        artist(s)
    """
    audio = EasyID3(mp3_filepath)
    artists = [_ for _ in audio.get("artist") if _]
    artists = [a.strip() for artist in artists for a in artist.split(",")]

    return artists


def high_pass_filter(y, sr, cutoff=150):
    """
    Apply a high-pass filter to remove low frequencies below 'cutoff' Hz.
    """
    nyquist = 0.5 * sr
    normal_cutoff = cutoff / nyquist
    # noinspection PyTupleAssignmentBalance
    b, a = butter(1, normal_cutoff, btype="high", analog=False)
    return filtfilt(b, a, y)


def get_track_length(file_path):
    """Retrieve the duration of an MP3 file from metadata without fully loading it."""
    audio = MP3(file_path)
    return audio.info.length  # Returns duration in seconds


def analyze_track(file_path: str) -> dict[str, str | list[str]]:
    """
    Analyze an audio file for rhythmic density, key (Major/Minor), and BPM.
    """
    y, sr = librosa.load(file_path, sr=None)
    track_duration = int(librosa.get_duration(y=y, sr=sr))
    duration = min(track_duration, 180)
    start_time = max(0, min(30, duration - 30))

    y, sr = librosa.load(file_path, sr=None, duration=duration, offset=start_time)

    if HPF:
        y = high_pass_filter(y, sr, cutoff=150)

    # Harmonic & Percussive Separation
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # Onset Strength (Rhythmic Density)
    onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr, hop_length=1024)
    rhythmic_density = np.mean(onset_env)  # Average onset strength

    # Key Estimation (Using Chroma Features)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_sum = chroma.sum(axis=1)  # Sum chroma activation per note
    root_index = np.argmax(chroma_sum)  # Most dominant note

    # Determine Major/Minor Mode
    # Identify Minor 2nd (♭2) Strength
    minor_2nd_index = (root_index + 1) % 12  # Minor 2nd is 1 semitone above root
    minor_2nd_strength = chroma[minor_2nd_index].sum()

    # Identify Major or Minor 3rd
    minor_third_index = (root_index + 3) % 12
    major_third_index = (root_index + 4) % 12

    minor_third_strength = chroma[minor_third_index].sum()
    major_third_strength = chroma[major_third_index].sum()

    # Determine Major/Minor Based on Thirds AND Minor 2nd
    if minor_2nd_strength > (major_third_strength * 0.5):  # If Minor 2nd is at least 50% as strong as Major 3rd
        key_type = "Minor"  # Override to Minor
    elif major_third_strength > minor_third_strength:
        key_type = "Major"
    elif minor_third_strength > major_third_strength:
        key_type = "Minor"
    else:
        key_type = "Mixed"

    # Categorization Based on Rhythmic Density
    if rhythmic_density > 1.8:  # Lower Combat threshold slightly
        rhythmic_category = "Rhythmic"
    elif rhythmic_density < 1.6:  # Raise Ambient threshold slightly
        rhythmic_category = "Ambient"
    else:
        rhythmic_category = "Mixed"

    # Categorization Based on Key + Rhythmic Type
    if rhythmic_category == "Rhythmic" and key_type == "Major":
        final_category = "Triumph"
    elif rhythmic_category == "Rhythmic" and key_type == "Minor":
        final_category = "Combat"
    elif rhythmic_category == "Rhythmic" and key_type == "Mixed":
        final_category = "Theme"
    elif rhythmic_category == "Ambient" and key_type == "Minor":
        final_category = "Dark"
    elif rhythmic_category == "Ambient" and key_type == "Major":
        final_category = "Light"
    elif rhythmic_category == "Ambient" and key_type == "Mixed":
        final_category = "Light"  # Light fallback
    elif rhythmic_category == "Mixed" and key_type == "Major":
        final_category = "Triumph"
    elif rhythmic_category == "Mixed" and key_type == "Minor":
        final_category = "Theme"
    else:
        final_category = "Theme"

    artists = get_artists_from_mp3_metadata(file_path)

    return {"mood": final_category, "artists": artists}
