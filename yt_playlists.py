"""
Get playlists from YouTube, download and analyze tracks, then create or update playlists.
"""

import glob
import json
import os
import re
import subprocess
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
    return re.sub(r"[^a-zA-Z0-9]", "-", name).strip("-")


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


def download_album(album_id: str, album_title: str, temp_dir: str) -> list[dict]:
    """
    Download all tracks from an album.

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

    track_data = []
    for track in album_info["tracks"]:
        track_id = track["videoId"]
        track_title = track["title"]

        print(f"Downloading: {track_title} ({track_id})")
        track_name = os.path.join(folder_name, f"{track_title}.mp3")

        subprocess.run(
            f'yt-dlp -x --audio-format mp3 --add-metadata --no-mtime -o "{track_name}" '
            f'"https://music.youtube.com/watch?v={track_id}"',
            cwd=folder_name,
            shell=True,
        )

        print("Analyzing Track")
        mood = analyze_track(track_name)
        artists = []
        for artist in album_info["artists"]:
            artists.append(artist["name"])

        track_data.append({track_title: {"artist": artists, "album": album_title, "mood": mood, "track_id": track_id}})

    return track_data


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
        artist_name = artist["artist"]
        artist_id = artist["browseId"]

        albums = get_artist_albums(artist_id)
        print(f"Albums for {artist_name}:")

        for album in albums:
            album_title = album["title"]
            if album_title in playlist_directory:
                continue  # Skip if album is already processed

            playlist_directory[album_title] = [{"playlist_id": album["audioPlaylistId"]}]

            with TemporaryDirectory() as temp_dir:
                track_data = download_album(album["browseId"], album_title, temp_dir)
                playlist_directory[album_title].extend(track_data)

        break  # Process only one artist

    return playlist_directory


def save_playlists(playlist_directory: dict, filename: str = "yt_playlists.json"):
    """
    Save the updated playlist directory to a JSON file.

    Args:
        playlist_directory: The updated playlist dictionary.
        filename: Path to the output JSON file.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(playlist_directory, f, indent=2)


def main():
    """
    Main function to fetch subscribed artists, process albums, and update playlists.
    """
    subscribed_artists = get_subscribed_artists()
    print(f"Found {len(subscribed_artists)} subscribed artists.")

    playlist_directory = load_existing_playlists()
    updated_playlists = process_artists(subscribed_artists, playlist_directory)

    save_playlists(updated_playlists)


if __name__ == "__main__":
    main()
