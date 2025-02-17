"""
Analyze audio for mood
"""
import glob

import librosa
import numpy as np
from librosa import feature
from mutagen.mp3 import MP3
from scipy.signal import butter, filtfilt

HPF = False  # Toggle high-pass filtering


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


def analyze_track(file_path, detail=False):
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

    # Estimate BPM
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, hop_length=1024, sparse=False)
    bpm = round(tempo.item())

    # Key Estimation (Using Chroma Features)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_sum = chroma.sum(axis=1)  # Sum chroma activation per note
    root_index = np.argmax(chroma_sum)  # Most dominant note
    root_note = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][root_index]

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

    if detail:
        # Print or return results
        return {
            "file": file_path,
            "root": root_note,
            "mode": key_type,
            "bpm": bpm,
            "density": rhythmic_density,
            "rhythmic_category": rhythmic_category,
            "final_category": final_category,
        }

    return final_category  # Only return "Combat", "Dark", "Triumph", etc.




def test_stub():
    """
    Adjust the return to get the full analysis

    """
    # Run analysis on tracks
    # styles = ["Ambient-Dark", "Combat", "Ambient-Light", "Theme"]
    styles = ["AC-Origins"]
    results_by_style = {}

    for style in styles:
        results = []
        for track in glob.glob(rf"C:\Users\wyrmwood\Dropbox\public\music\{style}\*.mp3"):
            analysis = analyze_track(track, detail=True)
            results.append(analysis)

        results_by_style[style] = results

        print(f"\n{style} Results:")
        avg_density = sum(r["density"] for r in results) / len(results)
        print(f"Average Density: {avg_density:.3f}")
        print(f"Max Density: {max(r['density'] for r in results):.3f}")
        print(f"Min Density: {min(r['density'] for r in results):.3f}")

        for r in results:
            print(
                f"{r['file']} → {r['final_category']} | Key: {r['root']} {r['mode']} | BPM: {r['bpm']} | Density: {r['density']:.3f}"
            )
