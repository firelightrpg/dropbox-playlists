"""
Websocket server

Listens for text combat_start or combat_end and opens the appropriate playlist.
"""

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

    def __init__(self):
        self._driver = None
        self._base_url = "https://music.youtube.com"
        self._dark_playlist = "PLOofa859fAd0PUbWTcjwQd0RtNMOoFT8_"
        self._combat_playlist = "PLOofa859fAd1M6SpAP7DwnkHLQYRCwuAh"

    @property
    def driver(self) -> WebDriver:
        """
        driver property
        """
        if self._driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            service = Service()
            self._driver = webdriver.Chrome(options=options, service=service)

        return self._driver

    def switch_to_window_by_playlist(self, playlist: str) -> None:
        """

        Args:
            playlist:
        """
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if playlist in self.driver.current_url:
                return

        self.driver.execute_script("window.open('', '_blank');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.driver.get(f"{self._base_url}/playlist?list={playlist}")

    def _toggle_playback(self, action: str) -> None:
        """
        Handles play and pause actions based on the current icon state.

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
                try:
                    shuffle_button = self.driver.find_element("xpath", "//yt-formatted-string[text()='Shuffle play']")
                    shuffle_button.click()
                except WebDriverException:
                    pass  # Ignore if play/ pause button is not found

    def play(self) -> None:
        """
        Starts playback if music is paused.
        """
        self._toggle_playback("play")

    def pause(self) -> None:
        """
        Pauses playback if music is playing.
        """
        self._toggle_playback("pause")

    def start_music(self, combat: bool = False) -> None:
        """

        Args:
            combat:
        """
        self.switch_to_window_by_playlist(self._dark_playlist if combat else self._dark_playlist)
        self.pause()
        self.switch_to_window_by_playlist(self._combat_playlist if combat else self._dark_playlist)
        self.play()


driver = Driver()
driver.start_music()


@APP.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
    pass
