"""
Websocket server for switching shuffled playlists
"""

import logging
import random
import os
import argparse
import threading
from datetime import datetime

from fastapi import FastAPI, WebSocket
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException
from starlette.websockets import WebSocketDisconnect
from ytmusicapi import YTMusic
from dotenv import load_dotenv


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

    def __new__(cls, headless: bool = False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance._headless = headless
            cls._instance.combat_playlist = COMBAT
            cls._instance.dark_playlist = DARK
            cls._instance.start_playlist = random.choice(list(playlists["start"].values()))
            cls._instance.base_url = "https://music.youtube.com/watch?&list={}&shuffle=1"
            cls._instance._current_playlist_type = "start"  # Track playlist type: "start", "combat", or "dark"
            cls._instance._last_command_time = datetime.now()
            cls._instance._monitoring = False
            cls._instance._monitor_thread = None
            cls._instance._setup_driver()
            # Navigate to START playlist after driver creation
            cls._instance._open_playlist(cls._instance.start_playlist)
            cls._instance._start_monitoring()
        else:
            # Update headless flag on existing instance (no restart)
            cls._instance._headless = headless

        return cls._instance

    def _setup_driver(self):
        if self._driver is not None:
            return  # Ensure we don't instantiate twice

        import os
        import platform
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options

        options = Options()
        # Note: headless Firefox can cause choppy/glitchy audio on some systems due to
        # missing GPU acceleration and different CPU scheduling. Use headless=True only
        # for non-audio-quality tests (CI, smoke tests, functional validation, etc.).
        if self._headless:
            options.add_argument("--headless")  # Enable headless mode only when requested

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
            root_profile_path = r"C:\\Users\\wyrmwood\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\j504w7ys.default-release"
            options.add_argument("-profile")
            options.add_argument(root_profile_path)
            self._driver = webdriver.Firefox(options=options)

    @property
    def driver(self) -> WebDriver:
        return self._driver

    def _open_playlist(self, playlist_id: str):
        """Opens a playlist by its ID, avoiding reload if already on the same playlist."""
        if not self._driver:
            return

        # Check if we're already on the correct playlist
        if playlist_id in self.driver.current_url:
            return

        logger.info(f"Opening playlist: {self._name_from_id(playlist_id)}")
        track_url = self.base_url.format(playlist_id)
        self.driver.get(track_url)

    def start_music(self, combat: bool = False):
        """Starts music playback, ensuring the right playlist is selected."""
        playlist = (
            random.choice(list(playlists["combat"].values()))
            if combat
            else random.choice(list(playlists["dark"].values()))
        )

        self._current_playlist_type = "combat" if combat else "dark"
        self._last_command_time = datetime.now()
        self._open_playlist(playlist)

    def _name_from_id(self, playlist_id: str) -> str:
        for category in playlists.values():
            for name, pid in category.items():
                if pid == playlist_id:
                    return name
        return "unknown"

    def _is_playlist_ended(self) -> bool:
        """Check if the current playlist has ended by examining YouTube Music player state."""
        try:
            # Check if we can find the play button (not pause button)
            # When music is playing, there's a pause button; when ended, there's a play button
            # Also check the progress bar and time remaining

            # Method 1: Check if player shows it's at the end
            current_time = self._driver.execute_script("""
                const player = document.querySelector('video');
                if (player) {
                    return {
                        currentTime: player.currentTime,
                        duration: player.duration,
                        ended: player.ended,
                        paused: player.paused
                    };
                }
                return null;
            """)

            if current_time and current_time.get('ended'):
                return True

            # Method 2: Check if we're very close to the end and paused
            if current_time and current_time.get('paused'):
                duration = current_time.get('duration', 0)
                current = current_time.get('currentTime', 0)
                if duration > 0 and (duration - current) < 2:  # Within 2 seconds of end
                    return True

            return False

        except (WebDriverException, Exception) as e:
            logger.debug(f"Error checking playlist state: {e}")
            return False

    def _rotate_start_playlist(self):
        """Rotate to a new random start playlist."""
        new_playlist = random.choice(list(playlists["start"].values()))
        # Ensure we pick a different playlist if possible
        if len(playlists["start"]) > 1:
            attempts = 0
            while new_playlist == self.start_playlist and attempts < 10:
                new_playlist = random.choice(list(playlists["start"].values()))
                attempts += 1

        self.start_playlist = new_playlist
        self._current_playlist_type = "start"
        logger.info(f"Auto-rotating to new start playlist: {self._name_from_id(new_playlist)}")
        self._open_playlist(new_playlist)

    def _monitor_playback(self):
        """Background thread that monitors playback and auto-rotates start playlists."""
        import time

        logger.info("Starting playback monitor thread")

        while self._monitoring:
            try:
                time.sleep(10)  # Check every 10 seconds

                # Only auto-rotate if we're on a "start" playlist
                if self._current_playlist_type != "start":
                    continue

                # Check if playlist has ended
                if self._is_playlist_ended():
                    logger.info("Start playlist ended, rotating to new start playlist")
                    self._rotate_start_playlist()

            except Exception as e:
                logger.error(f"Error in playback monitor: {e}", exc_info=True)
                time.sleep(5)  # Brief pause before retrying

        logger.info("Playback monitor thread stopped")

    def _start_monitoring(self):
        """Start the background monitoring thread."""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self._monitor_thread.start()

    def _stop_monitoring(self):
        """Stop the background monitoring thread."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)


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


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable with common truthy/falsey values."""
    raw = os.getenv(name)
    if raw is None:
        return default
    raw_lower = raw.strip().lower()
    if raw_lower in {"1", "true", "yes", "y", "on"}:
        return True
    if raw_lower in {"0", "false", "no", "n", "off"}:
        return False
    # Fallback: log and return default
    logger.warning("Invalid boolean for %s=%r, using default %s", name, raw, default)
    return default


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the websocket server."""
    parser = argparse.ArgumentParser(description="Websocket server for switching shuffled playlists")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the YouTube Music Firefox driver in headless mode",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Force non-headless mode (overrides env/--headless)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Load environment variables from a .env file if present
    load_dotenv()

    args = _parse_args()

    # Precedence: CLI > ENV > default(False)
    env_headless = _env_bool("HEADLESS", default=False)
    if args.no_headless:
        headless = False
    elif args.headless:
        headless = True
    else:
        headless = env_headless

    logger.info("Starting websocket server (headless=%s)", headless)

    # Instantiate Singleton BEFORE Uvicorn starts
    driver = Driver(headless=headless)
    import uvicorn

    uvicorn.run(APP, host="127.0.0.1", port=PORT, workers=1)
