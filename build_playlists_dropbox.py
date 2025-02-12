"""Script to generate Dropbox-hosted playlists for MP3 files.

This script scans a local directory for MP3 files, generates Dropbox shared links,
and creates a CSV playlist for each folder. Additionally, it consolidates all playlists
into a master CSV file.

The script expects Dropbox credentials and paths to be set via environment variables or a `.env` file.
"""

import os
import csv
from typing import Any

import dropbox
from dropbox.exceptions import AuthError
import logging
import glob
from dotenv import load_dotenv

from mutagen.easyid3 import EasyID3


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load environment variables from .env file
load_dotenv()

# Define required environment variables
REQUIRED_VARS = ["DROPBOX_ACCESS_TOKEN", "DROPBOX_ROOT_FOLDER", "LOCAL_ROOT_FOLDER"]
MISSING_VARS = [var for var in REQUIRED_VARS if var not in os.environ]

if MISSING_VARS:
    print(
        f"Error: The following required environment variables are missing: {', '.join(MISSING_VARS)}"
    )
    raise SystemExit(1)

# Load environment variables
DROPBOX_ACCESS_TOKEN = os.environ["DROPBOX_ACCESS_TOKEN"]
DROPBOX_ROOT_FOLDER = os.environ["DROPBOX_ROOT_FOLDER"]
LOCAL_ROOT_FOLDER = os.environ["LOCAL_ROOT_FOLDER"]

# Initialize Dropbox client and verify access token
try:
    dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    dbx.users_get_current_account()
except AuthError:
    print("Error: Dropbox access token is invalid or expired.")
    raise SystemExit(1)


def get_existing_shared_link(mp3_filepath: str) -> Any | None:
    """Retrieve an existing shared link for a given Dropbox file.

    Args:
        mp3_filepath: Path of the file in Dropbox.

    Returns:
        Shared link URL if it exists
    """
    links = dbx.sharing_list_shared_links(path=mp3_filepath).links
    for link in links:
        if link.path_lower == mp3_filepath.lower():
            logging.info(f"Existing link found for {mp3_filepath}: {link.url}")
            return link.url
    return None


def get_mp3_metadata(mp3_filepath: str) -> list[str]:
    """Extract album and contributing artists from an MP3 file.

    TODO - this shouldn't be producing errors - what is the return value when it's empty? - we're just adding these
    as tags, so just return a single list.

    Args:
        mp3_filepath:

    Returns:
        tags from mp3 metadata
    """
    audio = EasyID3(mp3_filepath)
    # figure out audio
    tags = []
    album = [_ for _ in audio.get("album") if _]
    if album:
        tags.extend(album)

    artists = [_ for _ in audio.get("artist") if _]
    if artists:
        artist_tags = [a.strip() for artist in artists for a in artist.split(",")]
        tags.extend(artist_tags)

    return tags


def get_or_create_shared_link(mp3_filepath: str) -> str:
    """Retrieve or create a shared link for a Dropbox file.

    Args:
        mp3_filepath: Path of the file in Dropbox.

    Returns:
        The shared link URL.
    """
    existing_link = get_existing_shared_link(mp3_filepath)
    if existing_link:
        return existing_link

    shared_link = dbx.sharing_create_shared_link_with_settings(mp3_filepath)
    url = shared_link.url
    logging.info(f"Created new link for {mp3_filepath}: {url}")
    return url


def create_playlists():
    """Generate a playlist CSV file for all MP3 files found recursively in LOCAL_ROOT_FOLDER.

    Scans for MP3 files, retrieves Dropbox shared links, and saves a CSV playlist.
    Tracks are tagged based on their folder hierarchy and mp3 metadata for album and artist(s).
    """
    playlist = []
    all_mp3_files = glob.glob(
        os.path.normpath(os.path.join(LOCAL_ROOT_FOLDER, "**", "*.mp3")), recursive=True
    )
    mp3_files = sorted(list(set(all_mp3_files)))

    for mp3_file in mp3_files:
        relative_path = os.path.relpath(mp3_file, LOCAL_ROOT_FOLDER)
        folder_structure = os.path.dirname(relative_path).split(os.sep)
        tags = folder_structure  # Include all parent folders as tags
        tags.extend(get_mp3_metadata(mp3_file))

        name = os.path.splitext(os.path.basename(mp3_file))[0]
        dropbox_file_path = os.path.join(DROPBOX_ROOT_FOLDER, relative_path).replace(
            "\\", "/"
        )

        logging.info(f"Getting shared link for {dropbox_file_path}")
        src = get_or_create_shared_link(dropbox_file_path)
        if src:
            playlist.append([name, src, "|".join(tags)])

    if not playlist:
        logging.warning("No playlist created.")
        return

    master_csv_filepath = os.path.normpath(
        os.path.join(LOCAL_ROOT_FOLDER, "master_playlist.csv")
    )
    with open(master_csv_filepath, "w", newline="", encoding="utf-8") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["name", "src", "tags"])
        csvwriter.writerows(playlist)
        logging.info(f"Playlist created: {master_csv_filepath}")


def main():
    """Main execution function.

    Generates individual and master playlists based on MP3 files.
    """
    create_playlists()


if __name__ == "__main__":
    main()
