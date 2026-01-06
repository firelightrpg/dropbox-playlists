"""
Websocket server for switching shuffled playlists
"""

import logging
import random

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from starlette.websockets import WebSocketDisconnect
from ytmusicapi import YTMusic


# Logging configuration
DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S"
FORMAT: str = "%(asctime)s.%(msecs)03d [%(levelname)s] [%(module)s.%(lineno)s:%(funcName)s] %(message)s"

logging.basicConfig(level=logging.INFO, format=FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

APP = FastAPI()
PORT = 26796

playlists = {
    "dark": {
        "council_of_9": "OLAK5uy_m1D_o2TQJpVuShY46eOjIzqeT_d_ffOKM",
        "dead_melodies": "OLAK5uy_n3sePlA6VMDr05B0kxjIFwnU1xeiOxxT4",
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
    "start": {
        "born_again": "OLAK5uy_kf-rwJJGIYaMii7yBxLDx0hXb6zc_cVrQ",
        "invincible": "OLAK5uy_liCXamJIm1qRUO4Yf5JrX1RGSOFyduLaQ",
        "last_kingdom": "OLAK5uy_mZIGETZHwMeRVHVO4Gh_tYqapGP2GkIb4",
        "kingdom_of_heaven": "OLAK5uy_nBJGbRP2Ei0bsysPMlUKu9ewztbcbv5VY",
        "destiny": "OLAK5uy_l7l9jJeZm2FisO-3dBAKWilvZ4tltIdJE",
        "kalots": "OLAK5uy_n8T7sbqNO2Bm87mbt3uHVaWC17hS2kEfY",
        "secession": "OLAK5uy_kUiga6aIUy2vl5qJjvu-3x1lNVVp62Nwc",
    },
}

DARK = playlists["dark"]["dead_melodies"]
COMBAT = playlists["combat"]["sarah_combat"]
START = random.choice(list(playlists["start"].values()))

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
            cls._instance.start_playlist = random.choice(list(playlists["start"].values()))
            cls._instance.base_url = "https://music.youtube.com/watch?&list={}&shuffle=1"
            cls._instance._setup_driver()
            # Navigate to START playlist after driver creation
            cls._instance._open_playlist(cls._instance.start_playlist)

        return cls._instance

    def _setup_driver(self):
        if self._driver is not None:
            return  # Ensure we don't instantiate twice

        import os
        import platform
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options

        options = Options()

        if platform.system() == "Linux":
            # Linux - use existing flatpak profile with uBlock installed
            tmp_dir_path = f"{os.environ['XDG_RUNTIME_DIR']}/app/org.mozilla.firefox/tmp"
            os.makedirs(tmp_dir_path, exist_ok=True)
            os.environ["TMPDIR"] = tmp_dir_path

            options.binary_location = "/var/lib/flatpak/exports/bin/org.mozilla.firefox"
            options.set_preference("media.autoplay.default", 0)  # 0=allow all, 1=block audible, 5=block all
            options.set_preference("media.autoplay.blocking_policy", 0)
            options.set_preference("media.autoplay.allow-muted", True)

            options.add_argument("-profile")
            options.add_argument(os.path.expanduser("~/.var/app/org.mozilla.firefox/.mozilla/firefox/21q8yu91.jukebox"))

            # Use local geckodriver in project directory
            geckodriver_path = os.path.join(os.path.dirname(__file__), "tmp/geckodriver")
            if os.path.exists(geckodriver_path):
                logger.debug(f"Using geckodriver at: {geckodriver_path}")
                service = Service(executable_path=geckodriver_path, log_output="tmp/gecko.log")
                # service = Service(GeckoDriverManager().install(), log_output="gecko.log")
                self._driver = webdriver.Firefox(service=service, options=options)

            else:
                # Fallback to system geckodriver
                logger.info("Using system geckodriver")
                self._driver = webdriver.Firefox(options=options)
        else:
            # Windows - use existing profile
            root_profile_path = r"C:\Users\wyrmwood\AppData\Roaming\Mozilla\Firefox\Profiles\j504w7ys.default-release"
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

        logger.info(f"Opening playlist: {self._name_from_id(playlist_id)}")
        track_url = self.base_url.format(playlist_id)
        self.driver.get(track_url)

    def start_music(self, combat=False):
        """
        Starts music playback, ensuring the right playlist is selected.
        """
        playlist = (
            random.choice(list(playlists["combat"].values()))
            if combat
            else random.choice(list(playlists["dark"].values()))
        )

        self._open_playlist(playlist)

    def _name_from_id(self, playlist_id: str) -> str:
        for category in playlists.values():
            for name, pid in category.items():
                if pid == playlist_id:
                    return name
        return "unknown"


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
                logger.info("Starting combat music")
                driver.start_music(combat=True)
            else:
                logger.info("Starting ambient music")
                driver.start_music(combat=False)
    except WebSocketDisconnect:
        logger.info("Websocket disconnected")
    finally:
        logger.debug("Websocket closed")


if __name__ == "__main__":
    # Instantiate Singleton BEFORE Uvicorn starts
    driver = Driver()
    import uvicorn

    uvicorn.run(APP, host="127.0.0.1", port=PORT, workers=1)
