#!/usr/bin/env python3
"""
Audio analysis using Essentia (runs on Linux - Debian/WSL).

This script uses Essentia for mood classification based on audio features.

Setup:
    pip install essentia

Usage:
    python3 analyze_essentia.py <audio_file>
    python3 analyze_essentia.py --batch <directory>

Remote usage (from WSL):
    ssh bifrost "cd ~/dropbox-playlists && python3 analyze_essentia.py --batch downloads"
"""

import argparse
import json
import sys
from pathlib import Path


def check_essentia():
    """Check if essentia is available."""
    try:
        import essentia
        import essentia.standard as es

        return True
    except ImportError:
        print("ERROR: essentia not installed", file=sys.stderr)
        print("Run: pip install essentia", file=sys.stderr)
        return False


def get_title_from_mp3(file_path: str) -> str:
    """Extract title from MP3 metadata, fallback to filename."""
    try:
        from mutagen.easyid3 import EasyID3

        audio = EasyID3(file_path)
        title = audio.get("title", [None])[0]
        if title:
            return title
    except Exception:
        pass
    return Path(file_path).stem


def analyze_track(file_path: str) -> dict:
    """
    Analyze a track using Essentia's audio features.

    Maps extracted features to mood categories:
    - Combat: high arousal (intense), low valence (dark/tense)
    - Triumph: high arousal (intense), high valence (bright/major)
    - Dark: low arousal (ambient), low valence (dark/tense)
    - Light: low arousal (ambient), high valence (bright/major)
    - Theme: middle zone
    """
    import essentia.standard as es

    # Load audio
    loader = es.MonoLoader(filename=file_path, sampleRate=44100)
    audio = loader()

    # Rhythm features
    rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
    bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)

    # If BPM is unreasonably high, it's likely detecting double-time
    if bpm > 160:
        bpm = bpm / 2

    # Energy
    rms = es.RMS()(audio)

    # Spectral features
    spectrum = es.Spectrum()(audio)
    centroid = es.Centroid()(spectrum)

    # Key detection
    key_extractor = es.KeyExtractor()
    key, scale, strength = key_extractor(audio)

    # Danceability (good proxy for "driving" quality)
    danceability, _ = es.Danceability()(audio)

    # Dynamic complexity
    dynamic_complexity = es.DynamicComplexity()(audio)[0]

    # Spectral flux - measures how much the spectrum changes over time
    # Low flux = sustained/ambient, high flux = rhythmic/percussive
    flux = es.Flux()(spectrum)

    # Zero-crossing rate - low for sustained/tonal, high for percussive/noisy
    # Typical values: sustained pads ~0.02, rhythmic ~0.1+
    zcr = es.ZeroCrossingRate()(audio)

    # Map to arousal/valence
    # Arousal: based on loudness, spectral activity, and rhythmic drive

    # Weight tempo by beat confidence - if no clear beat, don't trust BPM
    raw_tempo_score = min(1.0, bpm / 120)
    tempo_score = raw_tempo_score * max(
        0, beats_confidence
    )  # Scale by confidence (0-1)

    # RMS energy - scale so 0.1 RMS = 1.0 (loud)
    energy_score = min(1.0, rms / 0.1)

    # Spectral flux - higher = more change in spectrum
    flux_score = min(1.0, flux / 0.5)

    # Zero-crossing rate - higher = more percussive/driving
    # Typical values: sustained pads ~0.02, rhythmic ~0.1+
    zcr_score = min(1.0, zcr / 0.1)

    # Combine flux and zcr for "rhythmic activity" score
    rhythmic_score = (flux_score + zcr_score) / 2

    # Weight: energy 35%, rhythmic 45%, tempo 20%
    arousal = energy_score * 0.35 + rhythmic_score * 0.45 + tempo_score * 0.20

    # Compute mode_score and brightness for valence calculation
    mode_score = 1.0 if scale == "major" else 0.0
    brightness = float(centroid)  # Already 0-1 from Essentia's Centroid

    # Valence: based on mode (major=positive) and brightness
    # If key detection is weak, ignore key and use only brightness
    if strength < 0.3:
        valence = brightness
        valence_debug = f"valence=brightness({brightness:.2f}) [weak key]"
    else:
        key_weight = min(0.4, strength * 0.5)  # Reduce key influence
        brightness_weight = 1.0 - key_weight
        valence = mode_score * key_weight + brightness * brightness_weight
        valence_debug = f"valence={mode_score:.2f}*{key_weight:.2f} + {brightness:.2f}*{brightness_weight:.2f}"

    # Note: energy_score uses raw RMS (absolute volume), not normalized

    # Classify - improved logic
    # If very ambient (low zcr and low flux), force Dark
    if zcr < 0.025 and flux < 0.1:
        mood = "Dark"
    elif zcr < 0.03 and arousal < 0.6:
        mood = "Dark"
    elif arousal > 0.7:
        mood = "Triumph" if valence > 0.4 else "Combat"
    elif arousal > 0.6:
        # Allow Combat for high arousal even if zcr is low, if flux or tempo is high
        if zcr < 0.03 and (
            flux_score > 0.5 or tempo_score > 0.5 or dynamic_complexity > 5
        ):
            mood = "Combat"
        else:
            mood = "Theme" if zcr < 0.03 else "Combat"
    elif arousal < 0.55:
        mood = "Light" if valence > 0.4 else "Dark"
    else:
        mood = "Theme"

    # Debug output for key, key strength, valence
    # Uncomment the next line for detailed debug info per track
    # print(f"DEBUG: {get_title_from_mp3(file_path)} | key={key} {scale} ({strength:.2f}) | {valence_debug}")

    return {
        "mood": mood,
        "title": get_title_from_mp3(file_path),
        "arousal": float(arousal),
        "valence": float(valence),
        "bpm": float(bpm),
        "beat_confidence": float(beats_confidence),
        "flux": float(flux),
        "zcr": float(zcr),
        "key": f"{key} {scale}",
        "key_strength": float(strength),
        "brightness": float(brightness),
        "danceability": float(danceability),
        "rms": float(rms),
        "spectral_centroid": float(centroid),
        "dynamic_complexity": float(dynamic_complexity),
        "file": str(file_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze audio with Essentia")
    parser.add_argument("path", help="Audio file or directory to analyze")
    parser.add_argument(
        "--batch", "-b", action="store_true", help="Analyze all mp3s in directory"
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        help="Number of parallel processes for batch analysis (default: CPU count)",
    )

    args = parser.parse_args()

    if not check_essentia():
        sys.exit(1)

    if args.batch:
        import concurrent.futures
        import multiprocessing

        path = Path(args.path)
        files = list(path.rglob("*.mp3"))
        results = []
        workers = args.workers or multiprocessing.cpu_count()
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_file = {executor.submit(analyze_track, str(f)): f for f in files}
            for future in concurrent.futures.as_completed(future_to_file):
                f = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    if not args.json:
                        print(
                            f"[{result['mood']:7}] {result['title'][:30]:30} "
                            f"a={result['arousal']:5.2f} v={result['valence']:5.2f} "
                            f"zcr={result['zcr']:5.3f} {result['key']}"
                        )
                except Exception as e:
                    print(f"[ERROR] {f.name}: {e}", file=sys.stderr)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            # Summary
            print("\n" + "=" * 50)
            moods = {}
            for r in results:
                moods[r["mood"]] = moods.get(r["mood"], 0) + 1
            for mood, count in sorted(moods.items()):
                print(f"  {mood}: {count}")
            print(f"  Total: {len(results)}")
    else:
        try:
            result = analyze_track(args.path)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Mood: {result['mood']}")
                print(f"Arousal: {result['arousal']:.3f} (0=calm, 1=intense)")
                print(f"Valence: {result['valence']:.3f} (0=negative, 1=positive)")
                print(f"BPM: {result['bpm']:.1f}")
                print(f"Key: {result['key']}")
                print(f"Danceability: {result['danceability']:.3f}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
