import os
import csv
import dropbox
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Replace with your new Dropbox API access token
DROPBOX_ACCESS_TOKEN = "your_dropbox_token"
DROPBOX_ROOT_FOLDER = "/dropbox/path/to/root"
LOCAL_ROOT_FOLDER = "/local/path/to/root"

# Initialize Dropbox client
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)


def get_existing_shared_link(file_path):
    links = dbx.sharing_list_shared_links(path=file_path).links
    for link in links:
        if link.path_lower == file_path.lower():
            logging.info(f"Existing link found for {file_path}: {link.url}")
            return link.url
    return None


def get_or_create_shared_link(file_path):
    existing_link = get_existing_shared_link(file_path)
    if existing_link:
        return existing_link

    shared_link = dbx.sharing_create_shared_link_with_settings(file_path)
    url = shared_link.url
    logging.info(f"Created new link for {file_path}: {url}")
    return url


def create_playlist_for_folder(local_folder_path, dropbox_folder_path):
    playlist = []
    folder_name = os.path.basename(local_folder_path)

    for filename in os.listdir(local_folder_path):
        if filename.endswith(".mp3"):
            name = os.path.splitext(filename)[0]
            dropbox_file_path = os.path.join(dropbox_folder_path, filename).replace(
                "\\", "/"
            )

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
            f"No mp3 files found in {local_folder_path} or failed to create shared links."
        )


def main():
    for folder_name in os.listdir(LOCAL_ROOT_FOLDER):
        # Debugging: log the folder being processed
        logging.info(f"Processing folder: {folder_name}")

        local_folder_path = os.path.join(LOCAL_ROOT_FOLDER, folder_name)
        dropbox_folder_path = os.path.join(DROPBOX_ROOT_FOLDER, folder_name)
        if os.path.isdir(local_folder_path):
            create_playlist_for_folder(local_folder_path, dropbox_folder_path)


if __name__ == "__main__":
    main()
