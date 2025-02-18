"""
Get playlists from YouTube, download and analyze tracks, then create or update playlists.
"""

import json
import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor
from tempfile import TemporaryDirectory

from mutagen.easyid3 import EasyID3
from ytmusicapi import YTMusic

from analyze_track import analyze_track

# Initialize YouTube Music API
ytmusic = YTMusic("browser.json")


def get_subscribed_artists(limit: int = 100) -> list[dict]:
    """
    Fetch the list of subscribed artists from YouTube Music.

    Args:
        limit: Maximum number of artists to retrieve.

    Returns:
        A list of subscribed artist dictionaries.
    """
    return ytmusic.get_library_subscriptions(limit=limit)


def load_existing_playlists(filename: str = "yt_playlists.json") -> dict:
    """
    Load existing playlists from a JSON file if it exists.

    Args:
        filename: Path to the JSON file.

    Returns:
        A dictionary of existing playlists.
    """
    if os.path.exists(filename):
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_playlists(playlist_directory: dict, filename: str = "yt_playlists.json"):
    """
    Save the updated playlist directory to a JSON file.

    Args:
        playlist_directory: The updated playlist dictionary.
        filename: Path to the output JSON file.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(playlist_directory, f, indent=2)


def get_artist_albums(artist_id: str) -> list[dict]:
    """
    Retrieve the list of albums for a given artist.

    Args:
        artist_id: The YouTube Music browse ID of the artist.

    Returns:
        A list of album dictionaries.
    """
    artist_info = ytmusic.get_artist(artist_id)
    return artist_info.get("albums", {}).get("results", [])


def sanitize_filename(name: str) -> str:
    """
    Convert a string into a sanitized filename.

    Args:
        name: The original string.

    Returns:
        A sanitized string with non-alphanumeric characters replaced.
    """
    return re.sub(r"[^a-zA-Z0-9\-_]", "-", name).strip("-")


def get_mp3_metadata(mp3_filepath: str) -> list[str]:
    """
    Extract album and contributing artists from an MP3 file.

    Args:
        mp3_filepath: Path to the MP3 file.

    Returns:
        A list of extracted metadata tags.
    """
    audio = EasyID3(mp3_filepath)
    tags = []

    album = [_ for _ in audio.get("album", []) if _]
    tags.extend(album)

    artists = [_ for _ in audio.get("artist", []) if _]
    artist_tags = [a.strip() for artist in artists for a in artist.split(",")]
    tags.extend(artist_tags)

    return tags


def analyze_and_store(track_path: str) -> tuple[str, str]:
    """
    Analyze the mood of a track.

    Args:
        track_path: Path to the MP3 file.

    Returns:
        A tuple of (track path, analyzed mood).
    """
    return track_path, analyze_track(track_path)


def download_album(album_id: str, album_title: str, temp_dir: str) -> list[dict]:
    """
    Download all tracks from an album in batch and analyze them in parallel.

    Args:
        album_id: The YouTube Music browse ID of the album.
        album_title: The title of the album.
        temp_dir: The temporary directory for storing downloaded files.

    Returns:
        A list of track dictionaries containing metadata.
    """
    print(f"Downloading album: {album_title}")
    album_info = ytmusic.get_album(album_id)
    folder_name = os.path.join(temp_dir, sanitize_filename(album_title))
    os.makedirs(folder_name, exist_ok=True)

    # Collect track details
    tracks = album_info["tracks"]
    track_ids = [track["videoId"] for track in tracks]
    track_titles = [sanitize_filename(track["title"]) for track in tracks]
    track_paths = [os.path.join(folder_name, f"{title}.mp3") for title in track_titles]
    track_urls = [f"https://music.youtube.com/watch?v={track_id}" for track_id in track_ids]

    # Batch Download All Tracks at Once
    print(f"Downloading {len(track_ids)} tracks for album: {album_title}")
    subprocess.run(
        "yt-dlp -x --concurrent-fragments 5 --audio-format mp3 --no-mtime "
        f'-o "{folder_name}/%(title)s.%(ext)s" ' + " ".join(track_urls),
        cwd=folder_name,
        shell=True,
    )

    # Parallel Mood Analysis
    print("Analyzing Tracks...")
    with ProcessPoolExecutor() as executor:
        mood_results = dict(executor.map(analyze_and_store, track_paths))

    # Store Track Metadata
    artists = [artist["name"] for artist in album_info["artists"]]
    track_data = [
        {
            track_title: {
                "artist": artists,
                "album": album_title,
                "mood": mood_results.get(track_path, "unknown"),
                "track_id": track_id,
            }
        }
        for track_title, track_id, track_path in zip(track_titles, track_ids, track_paths)
    ]

    return track_data


def process_artist(artist: dict, playlist_directory: dict) -> dict:
    """
    Process a single artist, retrieve albums, and download tracks.

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

        # Reload JSON to ensure the latest state
        playlist_directory = load_existing_playlists()

        if album_title in playlist_directory:
            print(f"Skipping already processed album: {album_title}")
            continue

        print(f"Processing album: {album_title}")
        playlist_directory[album_title] = [{"playlist_id": album["audioPlaylistId"]}]

        with TemporaryDirectory() as temp_dir:
            track_data = download_album(album["browseId"], album_title, temp_dir)
            playlist_directory[album_title].extend(track_data)

        # Save progress after each album
        save_playlists(playlist_directory)

    return playlist_directory


def process_artists(artists: list[dict], playlist_directory: dict) -> dict:
    """
    Process subscribed artists, retrieve albums, and download tracks.

    Args:
        artists: List of subscribed artist dictionaries.
        playlist_directory: Dictionary of existing playlists.

    Returns:
        An updated playlist directory with newly processed albums and tracks.
    """
    for artist in artists:
        playlist_directory = process_artist(artist, playlist_directory)

    return playlist_directory


def main():
    """
    Main function to fetch subscribed artists, process albums, and update playlists.
    """
    subscribed_artists = get_subscribed_artists()
    print(f"Found {len(subscribed_artists)} subscribed artists.")

    playlist_directory = load_existing_playlists()
    updated_playlists = process_artists(subscribed_artists, playlist_directory)


if __name__ == "__main__":
    main()
