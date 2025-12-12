"""
Utility script to re-analyze downloaded tracks with updated settings.

This is useful for debugging and tuning characterization algorithms without
re-downloading files.
"""

import json
import os
from concurrent.futures import ProcessPoolExecutor

from analyze_track import analyze_track
from artist_settings import artist_settings_manager
from config import config


def find_all_tracks(base_dir: str = None) -> dict[str, list[str]]:
    """
    Find all MP3 files in the downloads directory, organized by artist.

    Args:
        base_dir: Base directory to search (defaults to config.DOWNLOAD_DIR)

    Returns:
        Dictionary mapping artist names to lists of track paths
    """
    if base_dir is None:
        base_dir = config.DOWNLOAD_DIR

    if not os.path.exists(base_dir):
        print(f"Download directory not found: {base_dir}")
        return {}

    tracks_by_artist = {}

    for artist_dir in os.listdir(base_dir):
        artist_path = os.path.join(base_dir, artist_dir)
        if not os.path.isdir(artist_path):
            continue

        tracks = []
        for root, dirs, files in os.walk(artist_path):
            for file in files:
                if file.endswith(".mp3"):
                    tracks.append(os.path.join(root, file))

        if tracks:
            tracks_by_artist[artist_dir] = tracks

    return tracks_by_artist


def analyze_artist_tracks(artist_name: str, track_paths: list[str]) -> list[dict]:
    """
    Analyze all tracks for a specific artist.

    Args:
        artist_name: Name of the artist
        track_paths: List of paths to track files

    Returns:
        List of analysis results
    """
    print(f"\nAnalyzing {len(track_paths)} tracks for {artist_name}...")

    # Use ProcessPoolExecutor for parallel analysis
    with ProcessPoolExecutor() as executor:
        track_infos = [(path, artist_name) for path in track_paths]
        results = list(executor.map(analyze_single_track, track_infos))

    return results


def analyze_single_track(track_info: tuple[str, str]) -> dict:
    """
    Analyze a single track.

    Args:
        track_info: Tuple of (track_path, artist_name)

    Returns:
        Analysis result with path
    """
    track_path, artist_name = track_info
    result = analyze_track(track_path, artist_name)
    result["path"] = track_path
    result["filename"] = os.path.basename(track_path)
    return result


def print_analysis_summary(artist_name: str, results: list[dict]):
    """Print a summary of analysis results."""
    mood_counts = {}
    for result in results:
        mood = result["mood"]
        mood_counts[mood] = mood_counts.get(mood, 0) + 1

    print(f"\nAnalysis Summary for {artist_name}:")
    print(f"Total tracks: {len(results)}")
    print(f"\nMood distribution:")
    for mood, count in sorted(mood_counts.items()):
        print(f"  {mood}: {count} ({count/len(results)*100:.1f}%)")

    if config.DEBUG_MODE and results:
        print(f"\nRhythmic density range:")
        densities = [r.get("rhythmic_density", 0) for r in results]
        print(f"  Min: {min(densities):.3f}")
        print(f"  Max: {max(densities):.3f}")
        print(f"  Avg: {sum(densities)/len(densities):.3f}")


def save_analysis_results(
    artist_name: str, results: list[dict], output_file: str = None
):
    """Save detailed analysis results to a JSON file."""
    if output_file is None:
        safe_name = artist_name.replace("/", "-").replace("\\", "-")
        output_file = os.path.join(config.JSON_DIR, f"{safe_name}_analysis.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDetailed results saved to: {output_file}")


def reanalyze_all():
    """Re-analyze all downloaded tracks."""
    tracks_by_artist = find_all_tracks()

    if not tracks_by_artist:
        print(
            "No tracks found. Make sure DEBUG_MODE is enabled and tracks have been downloaded."
        )
        return

    print(f"Found tracks for {len(tracks_by_artist)} artists")

    for artist_name, track_paths in tracks_by_artist.items():
        results = analyze_artist_tracks(artist_name, track_paths)
        print_analysis_summary(artist_name, results)
        save_analysis_results(artist_name, results)


def reanalyze_artist(artist_name: str):
    """Re-analyze tracks for a specific artist."""
    tracks_by_artist = find_all_tracks()

    if artist_name not in tracks_by_artist:
        print(f"No tracks found for artist: {artist_name}")
        print(f"Available artists: {', '.join(tracks_by_artist.keys())}")
        return

    track_paths = tracks_by_artist[artist_name]
    results = analyze_artist_tracks(artist_name, track_paths)
    print_analysis_summary(artist_name, results)
    save_analysis_results(artist_name, results)

    # Show example of how to create custom settings
    print(f"\nTo customize settings for {artist_name}, edit:")
    settings = artist_settings_manager.get_settings(artist_name)
    artist_settings_manager.save_settings(settings)
    print(f"  {os.path.join(config.SETTINGS_DIR, artist_name)}.json")


def interactive_tune():
    """Interactive mode to tune settings for an artist."""
    tracks_by_artist = find_all_tracks()

    if not tracks_by_artist:
        print(
            "No tracks found. Make sure DEBUG_MODE is enabled and tracks have been downloaded."
        )
        return

    print("Available artists:")
    artists = list(tracks_by_artist.keys())
    for i, artist in enumerate(artists, 1):
        print(f"  {i}. {artist} ({len(tracks_by_artist[artist])} tracks)")

    try:
        choice = int(input("\nSelect artist number (0 to exit): "))
        if choice == 0:
            return

        artist_name = artists[choice - 1]

        # Load current settings
        settings = artist_settings_manager.get_settings(artist_name)

        print(f"\nCurrent settings for {artist_name}:")
        print(f"  Rhythmic threshold: {settings.rhythmic_threshold}")
        print(f"  Ambient threshold: {settings.ambient_threshold}")
        print(f"  Minor 2nd sensitivity: {settings.minor_2nd_sensitivity}")

        # Analyze with current settings
        results = analyze_artist_tracks(artist_name, tracks_by_artist[artist_name])
        print_analysis_summary(artist_name, results)

        # Offer to adjust settings
        adjust = input("\nAdjust settings? (y/n): ").lower()
        if adjust == "y":
            try:
                settings.rhythmic_threshold = float(
                    input(f"Rhythmic threshold [{settings.rhythmic_threshold}]: ")
                    or settings.rhythmic_threshold
                )
                settings.ambient_threshold = float(
                    input(f"Ambient threshold [{settings.ambient_threshold}]: ")
                    or settings.ambient_threshold
                )
                settings.minor_2nd_sensitivity = float(
                    input(f"Minor 2nd sensitivity [{settings.minor_2nd_sensitivity}]: ")
                    or settings.minor_2nd_sensitivity
                )

                artist_settings_manager.save_settings(settings)
                print("\nSettings saved. Re-analyzing...")

                # Re-analyze with new settings
                results = analyze_artist_tracks(
                    artist_name, tracks_by_artist[artist_name]
                )
                print_analysis_summary(artist_name, results)
                save_analysis_results(artist_name, results)
            except ValueError:
                print("Invalid input. Settings not changed.")

    except (ValueError, IndexError):
        print("Invalid selection.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "all":
            reanalyze_all()
        elif command == "tune":
            interactive_tune()
        elif command == "list":
            tracks_by_artist = find_all_tracks()
            print("Downloaded artists:")
            for artist, tracks in tracks_by_artist.items():
                print(f"  {artist}: {len(tracks)} tracks")
        else:
            # Assume it's an artist name
            reanalyze_artist(command)
    else:
        print("Usage:")
        print("  python reanalyze_tracks.py all          # Re-analyze all artists")
        print("  python reanalyze_tracks.py tune         # Interactive tuning mode")
        print("  python reanalyze_tracks.py list         # List downloaded artists")
        print("  python reanalyze_tracks.py <artist>     # Re-analyze specific artist")
