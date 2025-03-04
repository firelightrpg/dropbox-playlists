"""
Create playlists from a json
"""

import json

from ytmusicapi import YTMusic

ytmusic = YTMusic("browser.json")
# Load the JSON data
with open("jsons/elder-scrolls-tracks.json", "r", encoding="utf-8") as f:
    data = json.load(f)

playlists = {"Dark": [], "Combat": []}

artist = ""
album = "Elder"
for mood in ("Dark", "Combat"):
    new_tracks = {
        t["track_id"]
        for album_title, album_tracks in data.items()
        for t in album_tracks
        if t["mood"] == mood
        and (not artist or artist in t["artist"])  # Ignore if artist is empty
        and (not album or album in album_title)  # Ignore if album is empty
    }
    playlists[mood] = list(
        set(playlists[mood]) | new_tracks
    )  # Merge without duplicates


response = ytmusic.create_playlist(
    "Elder-Scrolls-Combat", "Combat", "PUBLIC", video_ids=playlists["Combat"]
)
print(f"combat: {response}")
response = ytmusic.create_playlist(
    "Elder-Scrolls-Dark", "Dark Ambient", "PUBLIC", video_ids=playlists["Dark"]
)
print(f"dark: {response}")
