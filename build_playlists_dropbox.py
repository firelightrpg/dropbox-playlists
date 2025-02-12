"""Script to generate Dropbox-hosted playlists for MP3 files.

This script scans a local directory for MP3 files, generates Dropbox shared links,
and creates a CSV playlist for each folder. The script expects Dropbox credentials
and paths to be set via environment variables or a `.env` file.
"""

import os
import csv
import dropbox
from dropbox.exceptions import AuthError
import logging
from dotenv import load_dotenv

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

def get_existing_shared_link(file_path):
    """Retrieve an existing shared link for a given Dropbox file.

    Args:
        file_path (str): Path of the file in Dropbox.

    Returns:
        str or None: Shared link URL if it exists, otherwise None.
    """
    links = dbx.sharing_list_shared_links(path=file_path).links
    for link in links:
        if link.path_lower == file_path.lower():
            logging.info(f"Existing link found for {file_path}: {link.url}")
            return link.url
    return None

def get_or_create_shared_link(file_path):
    """Retrieve or create a shared link for a Dropbox file.

    Args:
        file_path (str): Path of the file in Dropbox.

    Returns:
        str: The shared link URL.
    """
    existing_link = get_existing_shared_link(file_path)
    if existing_link:
        return existing_link

    shared_link = dbx.sharing_create_shared_link_with_settings(file_path)
    url = shared_link.url
    logging.info(f"Created new link for {file_path}: {url}")
    return url

def create_playlist_for_folder(local_folder_path, dropbox_folder_path):
    """Generate a playlist CSV file for a given local folder.

    Scans for MP3 files, retrieves Dropbox shared links, and saves a CSV playlist.

    Args:
        local_folder_path (str): Local directory containing MP3 files.
        dropbox_folder_path (str): Corresponding Dropbox folder path.
    """
    playlist = []
    folder_name = os.path.basename(local_folder_path)

    for filename in os.listdir(local_folder_path):
        if filename.endswith(".mp3"):
            name = os.path.splitext(filename)[0]
            dropbox_file_path = os.path.join(dropbox_folder_path, filename).replace("\\", "/")

            logging.info(f"Getting shared link for {dropbox_file_path}")
            src = get_or_create_shared_link(dropbox_file_path)
            if src:
                playlist.append([name, src, folder_name])

    if playlist:
        csv_filename = f"{folder_name}_playlist.csv"
        csv_filepath = os.path.join(local_folder_path, csv_filename)
        with open(csv_filepath, "w", newline="", encoding="utf-8") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(["name", "src", "tags"])
            csvwriter.writerows(playlist)
        logging.info(f"Playlist created: {csv_filepath}")
    else:
        logging.warning(
            f"No MP3 files found in {local_folder_path} or failed to create shared links."
        )

def main():
    """Main execution function.

    Iterates through local directories, checking for existing playlists.
    If none exist, it generates a new one.
    """
    for folder_name in os.listdir(LOCAL_ROOT_FOLDER):
        folder_path = os.path.join(LOCAL_ROOT_FOLDER, folder_name)
        if not os.path.isdir(folder_path) or os.path.exists(
            os.path.join(folder_path, f"{folder_name}_playlist.csv")
        ):
            continue

        logging.info(f"Processing folder: {folder_name}")
        local_folder_path = os.path.join(LOCAL_ROOT_FOLDER, folder_name)
        dropbox_folder_path = os.path.join(DROPBOX_ROOT_FOLDER, folder_name)
        if os.path.isdir(local_folder_path):
            create_playlist_for_folder(local_folder_path, dropbox_folder_path)

if __name__ == "__main__":
    main()
