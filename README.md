# Dropbox Playlist Generator

## Overview
This script scans a local directory for MP3 files, generates Dropbox shared links, and creates a master CSV playlist. It efficiently updates the playlist by adding new files and removing missing ones while preserving existing entries.

## Requirements
- Python 3.x
- Dropbox API access token
   - See [Drobox Developer](https://www.dropbox.com/developers/apps?_tk=pilot_lp&_ad=topbar4&_camp=myapps) 

### Dependencies
```bash
cd <workspace>
python -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

## Setup
1. Add the following environment variables **OR** Create a `.env` file in the same directory with the following:
   ```env
   DROPBOX_ACCESS_TOKEN=your_dropbox_token
   DROPBOX_ROOT_FOLDER=/path/to/your/dropbox/folder
   LOCAL_ROOT_FOLDER=/path/to/your/local/mp3/folder
   ```
## Usage
Run the script:
```sh
python -m abovevtt_playlist_db
```

## How It Works
- Loads the existing playlist directory (`playlist_directory.json`) if available.
- Scans for `.mp3` files in the `<LOCAL_ROOT_FOLDER>` directory.
- Compares with the playlist directory:
  - **New files** are processed and added.
  - **Missing files** are removed from the playlist directory.
     - **Note:** _This will not remove them from AboveVTT._
  - **Existing files** remain unchanged.
- Tags are added based on:
  - **MP3 metadata** (album and artist)
  - **Folder structure** (e.g., `Cool/Naru's Way.mp3` → tags: `Cool`)
  - **Mood classification** (see below)

### **Mood Classification**
The script analyzes the **character, emotion, and spirit** of each track into five broad moods:

| Mood     | Description  | Characteristics |
|----------|-------------|----------------|
| **Dark** | Ambient, minor key | Sparse rhythm, low energy |
| **Light** | Ambient, major key | Sparse rhythm, uplifting |
| **Combat** | High-intensity battle music | Rhythmic, minor key |
| **Triumph** | Victory themes | Rhythmic, major key |
| **Theme** | General-purpose soundtrack | Mixed rhythm, minor/mixed key |

### **Example Categorizations**
| Mood       | Example Track |
|------------|----------------------------------------------------------------|
| **Dark**   | [Sunshine (Adagio in D Minor)](https://music.youtube.com/watch?v=DUWTqXo4-io) |
| **Light**  | [A White Stallion Rampant](https://music.youtube.com/watch?v=-zud9S0Yydo) |
| **Combat** | [Defenders of the Realm](https://music.youtube.com/watch?v=66A0wy2l29U) |
| **Triumph** | [Clouds Over Northumbria](https://music.youtube.com/watch?v=yY6m4WVLxyU) |
| **Theme**  | [Ravensthorpe](https://music.youtube.com/watch?v=YALP8tHYg-w) |

## **Playlist Generation**
- **Creates** `playlist.csv` for import into AboveVTT with all the latest changes.
- **Categorized tracks** make it easy to filter by mood in AboveVTT.

## Managing AboveVTT Audio
AboveVTT does **not** have a "clear" function for audio. If you remove a file from your dropbox, it will **still** appear in AboveVTT until manually deleted. The audio list is stored in the browser cache, so:
1. Use **Export AUDIO** in AboveVTT to back up your track list.
2. If necessary, clear the AboveVTT audio storage:
   - Open the browser console (`F12` in most browsers).
   - Run:
     ```js
     localStorage.removeItem('audio.library.track')
     ```
   - Refresh AboveVTT.
3. Re-import the updated `playlist.csv` in AboveVTT.
4. Export your new audio!

## Notes
- This script does **not** modify existing Dropbox files, only gets or creates their shared links.
- If your Dropbox token expires, regenerate it and update `.env`.
  - This usually only lasts a couple of hours...
- This depends on audio being in a shared dropbox folder. Otherwise, the links will only work for you.

## Troubleshooting
### Missing Shared Links
If a shared link isn't found:
- Ensure the file exists in your Dropbox folder.
- Manually generate a shared link and re-run the script.

### Playlist Not Updating
- Ensure the script has **write permissions** to `playlist.csv`.
- Check the logs for errors (`log.txt` if enabled).
- When in doubt, delete the `playlist_directory.json` file. It will get regenerated, but will take some time to grab
all the links from dropbox, especially if you have a large library! 

---
**Author**: John, Wyrmwood, firelightrpg, <whatever expletive you'd like to refer to me as>  
**License**: AboveVTT Dropbox playlist © 2025 by John Felps is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 
