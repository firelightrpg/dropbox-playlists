"""
Websocket server for switching shuffled playlists
"""


import time

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from starlette.websockets import WebSocketDisconnect
from ytmusicapi import YTMusic

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options

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
        "last-kingdom": "OLAK5uy_mZIGETZHwMeRVHVO4Gh_tYqapGP2GkIb4",
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
}

DARK = playlists["dark"]["dead_melodies"]
COMBAT = playlists["combat"]["norse_combat"]
START = "OLAK5uy_mZIGETZHwMeRVHVO4Gh_tYqapGP2GkIb4"

# Reverse lookup: playlist ID -> human-readable name
PLAYLIST_NAMES: dict[str, str] = {
    playlist_id: name
    for category in playlists.values()
    for name, playlist_id in category.items()
}
PLAYLIST_NAMES[START] = "start"

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
                return

        options = Options()
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("media.autoplay.default", 0) # Autoplay allowed        
        service = Service(executable_path="/usr/local/bin/geckodriver")        
        self._driver = webdriver.Firefox(service=service, options=options)
        addon_path = "/home/grimwyrm/github/dropbox-playlists/ublock_origin.xpi"
        self._driver.install_addon(addon_path, temporary=True)
        self._driver.get("about:blank")
        time.sleep(4)

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
        name = PLAYLIST_NAMES.get(playlist_id, playlist_id)
        print(f"Switching to playlist: {name}")
        track_url = self.base_url.format(playlist_id)
        self.driver.get(track_url)
        # self._click_play()


    def _click_play(self):
        """
        Waits for the play button to appear and clicks it.
        """
        try:
            play_button = WebDriverWait(self._driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[aria-label="Play"]')
                )
            )
            play_button.click()
        except TimeoutException:
            print("Play button not found or already playing")

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
                driver.start_music(combat=True)
            else:
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
