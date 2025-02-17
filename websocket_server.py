import logging

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from starlette.websockets import WebSocketDisconnect

APP = FastAPI()
PORT = 26796


class Driver:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance.combat_playlist = "PLOofa859fAd1M6SpAP7DwnkHLQYRCwuAh"
            cls._instance.dark_playlist = "PLOofa859fAd0PUbWTcjwQd0RtNMOoFT8_"
            cls._instance._setup_driver()
        return cls._instance

    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        service = Service()
        self._driver = webdriver.Chrome(options=options, service=service)

    @property
    def driver(self) -> WebDriver:
        return self._driver

    def switch_to_window_by_playlist(self, playlist: str):
        """
        Switches to an open tab with the playlist, or opens a new one.

        Args:
            playlist: The playlist ID to switch to.
        """
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if playlist in self.driver.current_url:
                return
        self.driver.execute_script("window.open('', '_blank');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(f"https://music.youtube.com/playlist?list={playlist}")

    def play_pause(self, action: str):
        """
        Toggles play or pause based on the current icon state.

        Args:
            action: "play" to start playback, "pause" to stop playback.
        """
        try:
            icon_state = self.driver.find_element("css selector", "#play-pause-button yt-icon-shape").get_attribute(
                "class"
            )
            should_click = (action == "play" and "play" in icon_state) or (action == "pause" and "pause" in icon_state)

            if should_click:
                play_pause_button = self.driver.find_element("css selector", "#play-pause-button > #icon")
                play_pause_button.click()
        except WebDriverException:
            if action == "play":
                shuffle_visibility_button = self.driver.find_element(
                    "css selector", "div.yt-spec-touch-feedback-shape__fill"
                )
                shuffle_visibility_button.click()
                shuffle_button = self.driver.find_element("xpath", "//yt-formatted-string[text()='Shuffle play']")
                shuffle_button.click()

    def start_music(self, combat=False):
        """
        Handles playlist switching and playback state.

        Args:
            combat: Whether to switch to combat music.
        """
        playlist = self.dark_playlist if combat else self.combat_playlist
        self.switch_to_window_by_playlist(playlist)
        self.play_pause("pause")
        playlist = self.combat_playlist if combat else self.dark_playlist
        self.switch_to_window_by_playlist(playlist)
        self.play_pause("play")


# Instantiate the Singleton **BEFORE** Uvicorn starts
DRIVER = Driver()
DRIVER.start_music()


@APP.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles incoming WebSocket messages for switching music.

    Args:
        websocket: The WebSocket connection.
    """
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message == "combat_start":
                DRIVER.start_music(combat=True)
            else:
                DRIVER.start_music(combat=False)
    except WebSocketDisconnect:
        logging.info("Websocket disconnected")
    finally:
        logging.info("Websocket closed")


if __name__ == "__main__":
    import uvicorn

    # Run Uvicorn in a way that prevents multiple processes
    uvicorn.run(APP, host="127.0.0.1", port=PORT, workers=1)
