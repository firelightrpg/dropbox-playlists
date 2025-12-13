"""
Analyze tracks for a single artist - useful for tuning categorization parameters.

Usage:
    python analyze_artist.py                    # List subscribed artists
    python analyze_artist.py "Jeremy Soule"    # Analyze specific artist
    python analyze_artist.py --reanalyze "Jeremy Soule"  # Re-run analysis on existing downloads
"""

import argparse
import os
from pathlib import Path

from ytmusicapi import YTMusic

from analyze_track import analyze_track
from artist_settings import artist_settings_manager
from config import config


def list_subscribed_artists():
    """List all subscribed artists."""
    ytmusic = YTMusic("browser.json")
    artists = ytmusic.get_library_subscriptions(limit=100)

    print(f"\nSubscribed artists ({len(artists)}):\n")
    for i, artist in enumerate(artists, 1):
        print(f"  {i:3}. {artist['artist']}")
    print()


def get_downloaded_tracks(artist_name: str) -> list[Path]:
    """Get list of already-downloaded tracks for an artist."""
    from yt_playlists import sanitize_filename

    artist_dir = Path(config.DOWNLOAD_DIR) / sanitize_filename(artist_name)

    if not artist_dir.exists():
        return []

    tracks = []
    for album_dir in artist_dir.iterdir():
        if album_dir.is_dir():
            tracks.extend(album_dir.glob("*.mp3"))

    return sorted(tracks)


def analyze_existing_tracks(artist_name: str, show_details: bool = True):
    """Re-analyze already downloaded tracks for an artist."""
    tracks = get_downloaded_tracks(artist_name)

    if not tracks:
        print(f"\nNo downloaded tracks found for '{artist_name}'")
        print(f"Run without --reanalyze to download first.")
        return

    settings = artist_settings_manager.get_settings(artist_name)

    print(f"\nAnalyzing {len(tracks)} tracks for '{artist_name}'")
    print(
        f"Settings: rhythmic={settings.rhythmic_threshold}, ambient={settings.ambient_threshold}"
    )
    print("-" * 70)

    results = {"Combat": [], "Triumph": [], "Dark": [], "Light": [], "Theme": []}

    # Parallel analysis
    from concurrent.futures import ProcessPoolExecutor, as_completed

    def analyze_single(track_path):
        return track_path, analyze_track(str(track_path), artist_name)

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(analyze_single, tp): tp for tp in tracks}

        for future in as_completed(futures):
            track_path = futures[future]
            try:
                _, result = future.result()
                mood = result["mood"]
                results[mood].append(
                    {
                        "title": track_path.stem,
                        "album": track_path.parent.name,
                        "rhythmic_density": result.get("rhythmic_density", 0),
                        "key_type": result.get("key_type", "Unknown"),
                    }
                )

                if show_details:
                    print(
                        f"  [{mood:7}] {track_path.stem[:50]:50} "
                        f"(rd={result.get('rhythmic_density', 0):.2f}, key={result.get('key_type', '?')})"
                    )
            except Exception as e:
                print(f"  [ERROR] {track_path.stem}: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for mood, tracks in results.items():
        print(f"  {mood:8}: {len(tracks):3} tracks")

    print(f"\nTotal: {sum(len(t) for t in results.values())} tracks")

    return results


def download_and_analyze_artist(artist_name: str):
    """Download and analyze all albums for an artist."""
    ytmusic = YTMusic("browser.json")

    # Find artist
    artists = ytmusic.get_library_subscriptions(limit=100)
    artist = next(
        (a for a in artists if a["artist"].lower() == artist_name.lower()), None
    )

    if not artist:
        print(f"\nArtist '{artist_name}' not found in subscriptions.")
        print("Use `python analyze_artist.py` to list available artists.")
        return

    artist_id = artist["browseId"]
    print(f"\nFound artist: {artist['artist']} (ID: {artist_id})")

    # Get albums
    artist_info = ytmusic.get_artist(artist_id)
    albums = artist_info.get("albums", {}).get("results", [])

    print(f"Found {len(albums)} albums")

    # Import here to avoid circular imports
    from yt_playlists import download_album, sanitize_filename

    # Create download directory
    download_dir = os.path.join(config.DOWNLOAD_DIR, sanitize_filename(artist_name))
    os.makedirs(download_dir, exist_ok=True)

    print(f"Download directory: {os.path.abspath(download_dir)}")

    all_tracks = []
    errors = 0
    for album in albums:
        album_title = album["title"]
        print(f"\nProcessing: {album_title}")

        try:
            tracks = download_album(
                album["browseId"], album_title, download_dir, artist_name
            )
            all_tracks.extend(tracks)
        except Exception as e:
            print(f"  Error: {e}")
            errors += 1

    # Count actual files on disk
    from pathlib import Path

    mp3_files = list(Path(download_dir).rglob("*.mp3"))

    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"Tracks analyzed: {len(all_tracks)}")
    print(f"MP3 files on disk: {len(mp3_files)}")
    print(f"Albums with errors: {errors}")
    print(f"Download directory: {os.path.abspath(download_dir)}")
    print(f"\nTo re-analyze with different settings:")
    print(f"  1. Edit artist_settings/{sanitize_filename(artist_name)}.json")
    print(f'  2. Run: python analyze_artist.py --reanalyze "{artist_name}"')


def show_artist_settings(artist_name: str):
    """Show current settings for an artist."""
    settings = artist_settings_manager.get_settings(artist_name)

    print(f"\nSettings for '{artist_name}':")
    print(f"  rhythmic_threshold: {settings.rhythmic_threshold}")
    print(f"  ambient_threshold:  {settings.ambient_threshold}")
    print(f"  use_hpf:            {settings.use_hpf}")
    print(f"  hpf_cutoff:         {settings.hpf_cutoff}")
    print(f"  minor_2nd_sensitivity: {settings.minor_2nd_sensitivity}")
    print(f"  max_duration:       {settings.max_duration}")
    print(f"  start_offset:       {settings.start_offset}")
    print(f"  notes:              {settings.notes or '(none)'}")


def main():
    parser = argparse.ArgumentParser(description="Analyze tracks for a single artist")
    parser.add_argument(
        "artist",
        nargs="?",
        help="Artist name to analyze (omit to list all subscribed artists)",
    )
    parser.add_argument(
        "--reanalyze",
        "-r",
        action="store_true",
        help="Re-analyze existing downloads without re-downloading",
    )
    parser.add_argument(
        "--settings",
        "-s",
        action="store_true",
        help="Show current settings for the artist",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Show summary only, not per-track details",
    )

    args = parser.parse_args()

    if not args.artist:
        list_subscribed_artists()
        return

    if args.settings:
        show_artist_settings(args.artist)
        return

    if args.reanalyze:
        analyze_existing_tracks(args.artist, show_details=not args.quiet)
    else:
        download_and_analyze_artist(args.artist)


if __name__ == "__main__":
    main()
