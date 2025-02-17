import glob
import logging
import os.path
import random
import time

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from starlette.websockets import WebSocketDisconnect
from ytmusicapi import YTMusic

APP = FastAPI()
PORT = 26796
COMBAT = "PLOofa859fAd1M6SpAP7DwnkHLQYRCwuAh"
DARK = "PLOofa859fAd0PUbWTcjwQd0RtNMOoFT8_"
UBLOCK_PATH = os.path.join(
    os.path.expanduser("~"),
    r"AppData\Local\Google\Chrome\User Data\Default\Extensions\cjpalhdlnbpafiamejdnhcphjbkeiagm",
)
UBLOCK_LATEST = glob.glob(os.path.join(UBLOCK_PATH, "*"))[0]
YTMUSIC = YTMusic()


class Playlists:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.combat_playlist = YTMUSIC.get_playlist(COMBAT)
            cls._instance.dark_playlist = YTMUSIC.get_playlist(DARK)
            cls._instance._combat_tracks = None
            cls._instance._dark_tracks = None

        return cls._instance

    @property
    def combat_tracks(self):
        return [_["videoId"] for _ in self.combat_playlist["tracks"]]

    @property
    def dark_tracks(self):
        return [_["videoId"] for _ in self.dark_playlist["tracks"]]


PLAYLISTS = Playlists()


class Driver:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance.combat_playlist = COMBAT
            cls._instance.dark_playlist = DARK
            cls._instance.base_url = "https://music.youtube.com"
            cls._instance._setup_driver()
            cls._instance.start_music(combat=True)  # this won't autoplay
            time.sleep(1)
            cls._instance.start_music(combat=False)

        return cls._instance

    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        # options.add_argument("--headless")
        options.add_argument(f"--load-extension={UBLOCK_LATEST}")
        service = Service()
        self._driver = webdriver.Chrome(options=options, service=service)

    @property
    def driver(self) -> WebDriver:
        return self._driver

    def close_window(self, playlist: str) -> None:
        """

        Args:
            playlist:
        """
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if playlist in self.driver.current_url:
                self.driver.close()
                time.sleep(1)

    def start_music(self, combat=False):
        """
        Handles playlist switching and playback state.

        Args:
            combat (bool): Whether to switch to combat music.
        """
        # close previous, if exists
        # self.driver.close()

        # start new
        # format of url is https://music.youtube.com/watch?v=<track id>&list=<playlist id>
        if combat:
            track_id = random.choice(PLAYLISTS.combat_tracks)
            url = f"{self.base_url}/watch?v={track_id}&list={self.combat_playlist}"
        else:
            track_id = random.choice(PLAYLISTS.dark_tracks)
            url = f"{self.base_url}/watch?v={track_id}&list={self.dark_playlist}"

        self.driver.get(url)


# Instantiate the Singleton **BEFORE** Uvicorn starts
driver = Driver()


@APP.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket messages for switching music.

    Args:
        websocket (WebSocket): The WebSocket connection.
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
        logging.info("Websocket disconnected")
    finally:
        logging.info("Websocket closed")


if __name__ == "__main__":
    import uvicorn

    # Run Uvicorn in a way that prevents multiple processes
    uvicorn.run(APP, host="127.0.0.1", port=PORT, workers=1)
