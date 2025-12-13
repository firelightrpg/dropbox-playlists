"""
Websocket server for switching shuffled playlists
"""

import random

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from starlette.websockets import WebSocketDisconnect
from ytmusicapi import YTMusic

APP = FastAPI()
PORT = 26796

playlists = {
    "dark": {
        "council_of_9": "OLAK5uy_m1D_o2TQJpVuShY46eOjIzqeT_d_ffOKM",
        "dead_melodies": "OLAK5uy_n3sePlA6VMDr05B0kxjIFwnU1xeiOxxT4",
        "secession": "OLAK5uy_kUiga6aIUy2vl5qJjvu-3x1lNVVp62Nwc",
        "ghelfi_explore": "PLbHUA-o_5dgI6tffbLSHhgBVx8j3Y42sg",
        "ghelfi_cthulhu": "PLbHUA-o_5dgIOfXtdXSiTyul4_0IkfIk0",
        "norse_dark": "PLOofa859fAd1h-lPKuYSnj3dDjeGo43nt",
        "es_dark": "PLOofa859fAd0GJQvfYHaG-AusaUFodSB0",
        "sarah_dark": "PLOofa859fAd0Zkjx1Wy40xwyaRiTjmLT7",
        "angelic_dark": "PLj71cZ_KjA3Pb3fZLLfyiE0EOZiw0cVL0",
    },
    "combat": {
        "doom": "OLAK5uy_kSfcuckNboAymIpsoq6hb1y5TvtyUU6p4",
        "ghelfi_combat": "PLbHUA-o_5dgKIcvpPs10ftV9AdaV_hNN1",
        "norse_combat": "PLOofa859fAd0932pUaNEUP-b2J6Ly5Pcn",
        "es_combat": "PLOofa859fAd0CfvyGhDrcCoVusUu6K1pP",
        "sarah_combat": "PLOofa859fAd35COo1IK35DvkmaIDNJVRy",
        "epic_battle": "PLOofa859fAd3NWrXXykSR9-sY6ypAFomo",
        "angelic_battle": "OLAK5uy_nGR61e1t6ilQnSJTDcxt0hzKaSI-UDAN0",
    },
    "theme": {
        "Last Kingdom": "OLAK5uy_mZIGETZHwMeRVHVO4Gh_tYqapGP2GkIb4",
        "AudioMachine": "RDAOYmENuG8uYcGYZz9v53FP3g",
        "Zack Hemsey": "RDAO_V1-pywGQJ1b7c4eUDkv_Q",
        "Runfell": "RDAOjI7sSD-xfhzwydBVrKHImg",
        "Ludivico Einaudi": "RDAOcxQuz-ELu51ZpArhWuw9Xg",
        "Ninja Tracks": "RDAOsJqg6s67bVGfyAP_xhvqdQ",
        "Frida Johannsson": "RDAOqTxg0cAmbtlrTNsJDF87DA",
        "Sarah Schachner": "RDAOVWTPuk9dutMH5IUQvuRXaA",
        "Brad Derrick": "RDAOvPMKEr6qZ3scdMYECXpfKw",
        "Two Steps from Hell": "RDAO6GGjT7rs1JdgEco3wIgmTw",
        "Twelve Titans Music": "RDAOQwAKhnwpWvkSkshD2uTsIQ",
        "Eternal Eclipse": "RDAO6VCYoh2N-opk04YSfO1JwA",
        "Epic Music World": "RDAOmKU4UNbAk9lZ1JvJrNuxyA",
    },
}

DARK = playlists["dark"]["dead_melodies"]
COMBAT = playlists["combat"]["sarah_combat"]
START = random.choice(list(playlists["theme"].values()))


# DARK = playlists["dark"]["sarah_dark"]
# COMBAT = playlists["combat"]["ghelfi_combat"]

YTMUSIC = YTMusic()


class Playlists:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.combat_playlist = YTMUSIC.get_playlist(COMBAT)
            cls._instance.dark_playlist = YTMUSIC.get_playlist(DARK)

        return cls._instance

    @property
    def combat_tracks(self):
        return [_["videoId"] for _ in self.combat_playlist["tracks"]]

    @property
    def dark_tracks(self):
        return [_["videoId"] for _ in self.dark_playlist["tracks"]]


PLAYLISTS = Playlists()


class Driver:
    _instance = None

    """
    
    """
    # https://www.youtube.com/watch?&list=PLOofa859fAd1h-lPKuYSnj3dDjeGo43nt&pp=gAQB&shuffle=1&loop=1
    # https://www.youtube.com/watch?v=p81B2zlyz_M&list=PLOofa859fAd1h-lPKuYSnj3dDjeGo43nt&pp=gAQB
    # https://music.youtube.com/watch?playlist=PLOofa859fAd0932pUaNEUP-b2J6Ly5Pcn

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance.combat_playlist = COMBAT
            cls._instance.dark_playlist = DARK
            cls._instance.start_playlist = START
            cls._instance.base_url = (
                "https://music.youtube.com/watch?&list={}&shuffle=1"
            )
            cls._instance._setup_driver()
            # Navigate to START playlist after driver creation
            cls._instance._open_playlist(cls._instance.start_playlist)

        return cls._instance

    def _setup_driver(self):
        if self._driver is not None:
            return  # Ensure we don't instantiate twice

        root_profile_path = r"C:\Users\wyrmwood\AppData\Roaming\Mozilla\Firefox\Profiles\j504w7ys.default-release"

        options = webdriver.FirefoxOptions()
        options.add_argument("-profile")
        options.add_argument(root_profile_path)
        self._driver = webdriver.Firefox(options=options)

    @property
    def driver(self) -> WebDriver:
        return self._driver

    def _open_playlist(self, playlist_id: str):
        """
        Opens a playlist by its ID, avoiding reload if already on the same playlist.
        """
        if not self._driver:
            return
        # Check if we're already on the correct playlist
        if playlist_id in self.driver.current_url:
            return
        track_url = self.base_url.format(playlist_id)
        self.driver.get(track_url)

    def start_music(self, combat=False):
        """
        Starts music playback, ensuring the right playlist is selected.
        """
        playlist = self.combat_playlist if combat else self.dark_playlist
        self._open_playlist(playlist)


@APP.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket messages for switching music.
    """
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message == "combat_start":
                print("Starting combat music")
                driver.start_music(combat=True)
            else:
                print("Starting ambient music")
                driver.start_music(combat=False)
    except WebSocketDisconnect:
        print("Websocket disconnected")
    finally:
        print("Websocket closed")


if __name__ == "__main__":
    # Instantiate Singleton BEFORE Uvicorn starts
    driver = Driver()
    import uvicorn

    uvicorn.run(APP, host="127.0.0.1", port=PORT, workers=1)
