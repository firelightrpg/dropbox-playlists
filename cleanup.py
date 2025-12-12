"""
Utility to manage downloaded files and cleanup.
"""

import os
import shutil
from datetime import datetime

from config import config


def show_download_log():
    """Display the download log."""
    log_file = config.DOWNLOAD_LOG

    if not os.path.exists(log_file):
        print("No download log found.")
        return

    print(f"Download Log: {log_file}\n")
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Total entries: {len(lines)}\n")
    for line in lines:
        print(line.strip())


def show_disk_usage():
    """Show disk usage of download directory."""
    download_dir = config.DOWNLOAD_DIR

    if not os.path.exists(download_dir):
        print(f"Download directory not found: {download_dir}")
        return

    total_size = 0
    artist_sizes = {}

    for artist_dir in os.listdir(download_dir):
        artist_path = os.path.join(download_dir, artist_dir)
        if not os.path.isdir(artist_path):
            continue

        artist_size = 0
        file_count = 0

        for root, dirs, files in os.walk(artist_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    artist_size += size
                    total_size += size
                    if file.endswith(".mp3"):
                        file_count += 1
                except OSError:
                    pass

        artist_sizes[artist_dir] = (artist_size, file_count)

    print(f"Disk Usage for {download_dir}:\n")
    print(f"{'Artist':<30} {'Files':>8} {'Size':>12}")
    print("-" * 52)

    for artist, (size, count) in sorted(
        artist_sizes.items(), key=lambda x: x[1][0], reverse=True
    ):
        size_mb = size / (1024 * 1024)
        print(f"{artist:<30} {count:>8} {size_mb:>10.1f} MB")

    print("-" * 52)
    total_mb = total_size / (1024 * 1024)
    total_gb = total_size / (1024 * 1024 * 1024)
    print(
        f"{'TOTAL':<30} {sum(c for _, c in artist_sizes.values()):>8} {total_mb:>10.1f} MB ({total_gb:.2f} GB)"
    )


def cleanup_artist(artist_name: str):
    """Remove downloaded files for a specific artist."""
    artist_path = os.path.join(config.DOWNLOAD_DIR, artist_name)

    if not os.path.exists(artist_path):
        print(f"Artist directory not found: {artist_path}")
        return

    # Calculate size before deletion
    size = 0
    for root, dirs, files in os.walk(artist_path):
        for file in files:
            try:
                size += os.path.getsize(os.path.join(root, file))
            except OSError:
                pass

    size_mb = size / (1024 * 1024)

    confirm = input(f"Delete {artist_path} ({size_mb:.1f} MB)? (yes/no): ")
    if confirm.lower() == "yes":
        shutil.rmtree(artist_path)
        print(f"Deleted {artist_path}")
    else:
        print("Cancelled.")


def cleanup_all():
    """Remove all downloaded files."""
    download_dir = config.DOWNLOAD_DIR

    if not os.path.exists(download_dir):
        print(f"Download directory not found: {download_dir}")
        return

    show_disk_usage()
    print()

    confirm = input(f"Delete entire download directory {download_dir}? (yes/no): ")
    if confirm.lower() == "yes":
        shutil.rmtree(download_dir)
        print(f"Deleted {download_dir}")

        # Also clear the log
        if os.path.exists(config.DOWNLOAD_LOG):
            os.remove(config.DOWNLOAD_LOG)
            print(f"Deleted {config.DOWNLOAD_LOG}")
    else:
        print("Cancelled.")


def archive_downloads(archive_path: str = None):
    """Create an archive of downloaded files."""
    if archive_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = f"downloads_backup_{timestamp}"

    download_dir = config.DOWNLOAD_DIR

    if not os.path.exists(download_dir):
        print(f"Download directory not found: {download_dir}")
        return

    print(f"Creating archive: {archive_path}.zip")
    shutil.make_archive(archive_path, "zip", download_dir)

    archive_size = os.path.getsize(f"{archive_path}.zip") / (1024 * 1024)
    print(f"Archive created: {archive_path}.zip ({archive_size:.1f} MB)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cleanup.py log           # Show download log")
        print("  python cleanup.py usage         # Show disk usage")
        print("  python cleanup.py artist <name> # Delete specific artist")
        print("  python cleanup.py all           # Delete all downloads")
        print("  python cleanup.py archive       # Create backup archive")
    else:
        command = sys.argv[1]

        if command == "log":
            show_download_log()
        elif command == "usage":
            show_disk_usage()
        elif command == "artist" and len(sys.argv) > 2:
            cleanup_artist(sys.argv[2])
        elif command == "all":
            cleanup_all()
        elif command == "archive":
            if len(sys.argv) > 2:
                archive_downloads(sys.argv[2])
            else:
                archive_downloads()
        else:
            print(f"Unknown command: {command}")
