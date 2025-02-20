"""
Websocket server for switching shuffled playlists
"""

import glob
import os

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from starlette.websockets import WebSocketDisconnect
from ytmusicapi import YTMusic

APP = FastAPI()
PORT = 26796
COMBAT = "PLOofa859fAd0932pUaNEUP-b2J6Ly5Pcn"  # Norse
DARK = "PLOofa859fAd1h-lPKuYSnj3dDjeGo43nt"  # Norse
UBLOCK_PATH = os.path.join(
    os.path.expanduser("~"),
    r"AppData\Local\Google\Chrome\User Data\Default\Extensions\cjpalhdlnbpafiamejdnhcphjbkeiagm",
)
UBLOCK_LATEST = glob.glob(os.path.join(UBLOCK_PATH, "*"))[0]
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
            cls._instance.base_url = (
                "https://music.youtube.com/watch?&list={}&shuffle=1"
            )
            cls._instance._setup_driver()

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

    def start_music(self, combat=False):
        """
        Starts music playback, ensuring the right playlist is selected.
        """
        playlist = self.combat_playlist if combat else self.dark_playlist

        # Check if we're already on the correct playlist
        if playlist in self.driver.current_url:
            return

        track_url = self.base_url.format(playlist)

        self.driver.get(track_url)


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
