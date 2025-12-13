"""
Get playlists from YouTube, download and analyze tracks, then create or update playlists.
"""

import concurrent.futures
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Any

from ytmusicapi import YTMusic

from analyze_track import analyze_track
from config import config

# Initialize YouTube Music API
ytmusic = YTMusic("browser.json")
json_lock = threading.Lock()


def get_subscribed_artists(limit: int = 100) -> list[dict]:
    """Fetch the list of subscribed artists from YouTube Music."""
    return ytmusic.get_library_subscriptions(limit=limit)


def load_existing_playlists(
    filename: str = os.path.join(config.JSON_DIR, "elder-scrolls-tracks.json")
) -> dict:
    """Load existing playlists from a JSON file if it exists."""
    if os.path.exists(filename):
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_playlists(
    playlist_directory: dict,
    filename: str = os.path.join(config.JSON_DIR, "elder-scrolls-tracks.json"),
):
    """Save the updated playlist directory to a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(playlist_directory, f, indent=2, ensure_ascii=False)

    time.sleep(2)


def get_artist_albums(artist_id: str) -> list[dict]:
    """Retrieve the list of albums for a given artist."""
    artist_info = ytmusic.get_artist(artist_id)
    return artist_info.get("albums", {}).get("results", [])


def sanitize_filename(name: str) -> str:
    """Convert a string into a sanitized filename."""
    return re.sub(r"[^a-zA-Z0-9\-_]", "-", name).strip("-")


def log_download(artist_name: str, album_title: str, folder_path: str):
    """Log downloaded files for later manual cleanup."""
    if not config.DEBUG_MODE:
        return

    log_file = config.DOWNLOAD_LOG
    timestamp = datetime.now().isoformat()

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {artist_name} | {album_title} | {folder_path}\n")


def analyze_and_store(track_info: tuple[str, str]) -> tuple[str, dict[str, Any]]:
    """Analyze the mood of a track.

    Args:
        track_info: Tuple of (track_path, artist_name)
    """
    track_path, artist_name = track_info
    return track_path, analyze_track(track_path, artist_name)


def download_track(track_id: str, track_title: str, folder_name: str) -> str | None:
    """Download a single track using yt-dlp."""
    track_filename = f"{track_title}.mp3"
    track_path = os.path.join(folder_name, track_filename)

    # Skip if file already exists and we're in debug mode
    if (
        config.DEBUG_MODE
        and config.SKIP_EXISTING_DOWNLOADS
        and os.path.exists(track_path)
    ):
        print(f"Skipping existing: {track_title}")
        return track_path

    completed_process = subprocess.run(
        f'yt-dlp -x --audio-format mp3 --add-metadata --no-mtime -o "{track_filename}" '
        f"--cookies-from-browser firefox "
        f'"https://music.youtube.com/watch?v={track_id}" ',
        cwd=folder_name,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed_process.returncode:
        raise RuntimeError(completed_process.stdout.decode())

    return track_path


def download_album(
    album_id: str, album_title: str, temp_dir: str, artist_name: str = None
) -> list[dict]:
    """Download all tracks from an album concurrently, then analyze them.

    Args:
        album_id: YouTube Music album ID
        album_title: Title of the album
        temp_dir: Directory to store downloaded files
        artist_name: Name of the artist (for settings and logging)
    """
    print(f"Downloading album: {album_title}")
    album_info = ytmusic.get_album(album_id)
    folder_name = os.path.join(temp_dir, sanitize_filename(album_title))
    os.makedirs(folder_name, exist_ok=True)

    tracks = album_info["tracks"]

    # Log download if in debug mode
    if config.DEBUG_MODE:
        log_download(artist_name or "Unknown", album_title, folder_name)

    # Parallel Download
    downloaded_tracks = {}
    print(f"Downloading {len(tracks)} tracks for album: {album_title}")
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_track = {
            executor.submit(
                download_track,
                track["videoId"],
                sanitize_filename(track["title"]),
                folder_name,
            ): track
            for track in tracks
        }

        for future in concurrent.futures.as_completed(future_to_track):
            track = future_to_track[future]
            try:
                track_path = future.result()
                if track_path:
                    downloaded_tracks[track_path] = track
            except Exception as e:
                print(f"  Failed to download '{track['title']}': {e}")

    # Parallel Mood Analysis
    print("Analyzing Tracks...")
    with ProcessPoolExecutor() as executor:
        # Pass both track_path and artist_name for artist-specific settings
        track_infos = [
            (track_path, artist_name) for track_path in downloaded_tracks.keys()
        ]
        results = dict(executor.map(analyze_and_store, track_infos))

    # Store Track Metadata
    track_data = [
        {
            "title": track["title"],
            "artist": results[track_path]["artists"],
            "mood": results[track_path]["mood"],
            "track_id": track["videoId"],
            # Include debug info if in debug mode
            **(
                {
                    "rhythmic_density": results[track_path].get("rhythmic_density"),
                    "key_type": results[track_path].get("key_type"),
                }
                if config.DEBUG_MODE
                else {}
            ),
        }
        for track_path, track in downloaded_tracks.items()
    ]

    return track_data


def process_artist(artist: dict, playlist_directory: dict) -> dict:
    """
    Process a single artist, retrieve albums, and download tracks.

    Ensures that JSON updates are serialized to prevent race conditions.

    Args:
        artist: Artist dictionary containing name and ID.
        playlist_directory: Dictionary of existing playlists.

    Returns:
        An updated playlist directory with newly processed albums and tracks.
    """
    artist_name = artist["artist"]
    artist_id = artist["browseId"]

    albums = get_artist_albums(artist_id)
    print(f"Processing artist: {artist_name} - Found {len(albums)} albums.")

    for album in albums:
        album_title = album["title"]
        if "Elder" not in album_title or "Oblivion" in album_title:
            continue

        # Reload JSON inside the lock to get the latest state
        with json_lock:
            playlist_directory = load_existing_playlists()

            if album_title in playlist_directory:
                print(f"Skipping already processed album: {album_title}")
                continue

            print(f"Processing artist: {artist_name} - album: {album_title}")
            playlist_directory[album_title] = []

        # Use persistent directory in debug mode, temporary otherwise
        if config.DEBUG_MODE:
            # Create persistent directory for this artist
            download_dir = os.path.join(
                config.DOWNLOAD_DIR, sanitize_filename(artist_name)
            )
            os.makedirs(download_dir, exist_ok=True)

            track_data = download_album(
                album["browseId"], album_title, download_dir, artist_name
            )

            # Update the playlist data inside the lock
            with json_lock:
                playlist_directory[album_title].extend(track_data)
                save_playlists(playlist_directory)  # Save after each album
                print(
                    f"Saved {len(track_data)} tracks for {artist_name} - {album_title}"
                )
        else:
            # Production mode: use temporary directory (auto-cleanup)
            with TemporaryDirectory() as temp_dir:
                track_data = download_album(
                    album["browseId"], album_title, temp_dir, artist_name
                )

                # Update the playlist data inside the lock
                with json_lock:
                    playlist_directory[album_title].extend(track_data)
                    save_playlists(playlist_directory)  # Save after each album
                    print(
                        f"Saved {len(track_data)} tracks for {artist_name} - {album_title}"
                    )

        print(f"Finished processing artist: {artist_name} - album: {album_title}.")

    print(f"Finished processing artist: {artist_name}.")

    return playlist_directory


def process_artists(artists: list[dict], playlist_directory: dict) -> dict:
    """Process subscribed artists, retrieve albums, and download tracks."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_artist = {
            executor.submit(process_artist, artist, playlist_directory): artist
            for artist in artists
        }

        for future in concurrent.futures.as_completed(future_to_artist):
            playlist_directory.update(future.result())

    return playlist_directory


def main():
    """Main function to fetch subscribed artists, process albums, and update playlists."""
    subscribed_artists = get_subscribed_artists()
    print(f"Found {len(subscribed_artists)} subscribed artists.")

    elder_artists = ["Brad Derrick", "Jeremy Soule", "Inon Zur"]
    subscribed_artists = [
        artist
        for artist in subscribed_artists
        if any(a in artist["artist"] for a in elder_artists)
    ]

    playlist_directory = load_existing_playlists()
    process_artists(subscribed_artists, playlist_directory)


if __name__ == "__main__":
    main()
