"""
Websocket and HTTP server for switching finite music cues.
Plays isolated single tracks without playlist chaining, enforces
silence states, and provides HTTP trigger links for markdown notes.
"""

import asyncio
import os
import random
import sys
import time
import traceback
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from starlette.websockets import WebSocketDisconnect

APP = FastAPI()
PORT = 26796

# Playback parameters (seconds)
COMBAT_PRE_ROLL_SILENCE = 1.5
POST_COMBAT_COOLDOWN = 30.0
FADE_DURATION = 6.0

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

DARK = random.choice(list(playlists["dark"].values()))
COMBAT = random.choice(list(playlists["combat"].values()))


class Driver:
    _instance: Optional["Driver"] = None

    def __new__(cls) -> "Driver":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._driver = None
            cls._instance.combat_playlist = COMBAT
            cls._instance.dark_playlist = DARK
            cls._instance._setup_driver()
        return cls._instance

    def _setup_driver(self) -> None:
        if self._driver is not None:
            return

        print("[Driver] Initializing Firefox with geckodriver...")
        options = Options()
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("media.autoplay.default", 0)
        service = Service(executable_path="/usr/local/bin/geckodriver")
        driver_instance = webdriver.Firefox(service=service, options=options)

        addon_path = "/home/grimwyrm/github/dropbox-playlists/ublock_origin.xpi"
        if not os.path.exists(addon_path):
            addon_path = "/home/grim/github/dropbox-playlists/ublock_origin.xpi"

        if os.path.exists(addon_path):
            print(f"[Driver] Installing uBlock Origin from: {addon_path}")
            driver_instance.install_addon(addon_path, temporary=True)
        else:
            print(f"[Driver] Warning: Addon not found at {addon_path}, continuing without it.")

        driver_instance.get("about:blank")
        time.sleep(2)
        self._driver = driver_instance
        print("[Driver] Browser initialized.")

    def play_category(self, combat: bool = False) -> None:
        if not self._driver:
            return
        playlist_id = self.combat_playlist if combat else self.dark_playlist
        url = f"https://music.youtube.com/watch?list={playlist_id}&shuffle=1"
        print(f"[Driver] Opening {'combat' if combat else 'dark'} playlist: {url}")
        self._driver.get(url)
        self.set_volume(1.0)
        self._arm_auto_fade_and_stop()

    def _arm_auto_fade_and_stop(self) -> None:
        if not self._driver:
            return
        js = """
        const v = document.querySelector('video');
        if (v && !v._fade_trap_armed) {
            v._fade_trap_armed = true;
            v.loop = false;

            const checkTailInterval = setInterval(() => {
                if (!v || v.paused) return;

                if (v.duration && (v.duration - v.currentTime <= 6.0) && !v._tail_fading) {
                    v._tail_fading = true;
                    const fadeDuration = (v.duration - v.currentTime) * 1000;
                    const startVol = v.volume;
                    const startTime = performance.now();

                    const fadeTimer = setInterval(() => {
                        const elapsed = performance.now() - startTime;
                        const progress = Math.min(1.0, elapsed / Math.max(100, fadeDuration));
                        v.volume = Math.max(0.0, startVol * Math.pow(1.0 - progress, 2));

                        if (progress >= 1.0) {
                            clearInterval(fadeTimer);
                            clearInterval(checkTailInterval);
                            v.pause();
                            v.volume = 1.0;
                            v._tail_fading = false;
                        }
                    }, 50);
                }
            }, 300);

            v.addEventListener('ended', (e) => {
                e.stopImmediatePropagation();
                v.pause();
                v.volume = 1.0;
                v._tail_fading = false;
            }, true);
        }
        """
        try:
            self._driver.execute_script(js)
        except Exception as e:
            print(f"[Driver] Warning arming fade trap: {e}")

    def pause_media(self) -> None:
        if not self._driver:
            return
        try:
            self._driver.execute_script("const v = document.querySelector('video'); if (v) v.pause();")
        except Exception as e:
            print(f"[Driver] Pause error: {e}")

    def set_volume(self, volume: float) -> None:
        if not self._driver:
            return
        try:
            clamped = max(0.0, min(1.0, volume))
            self._driver.execute_script(f"const v = document.querySelector('video'); if (v) v.volume = {clamped};")
        except Exception as e:
            print(f"[Driver] Volume error: {e}")

    def fade_out_dom(self, duration_sec: float = FADE_DURATION) -> None:
        if not self._driver:
            return
        js_fade = f"""
        const v = document.querySelector('video');
        if (v && !v.paused) {{
            const duration = {duration_sec} * 1000;
            const startVol = v.volume;
            const startTime = performance.now();
            
            const fadeInterval = setInterval(() => {{
                const elapsed = performance.now() - startTime;
                const progress = Math.min(1.0, elapsed / duration);
                
                v.volume = Math.max(0.0, startVol * Math.pow(1.0 - progress, 2));
                
                if (progress >= 1.0) {{
                    clearInterval(fadeInterval);
                    v.pause();
                    v.volume = 1.0;
                }}
            }}, 50);
        }}
        """
        try:
            self._driver.execute_script(js_fade)
        except Exception as e:
            print(f"[Driver] Native fade error: {e}")


class AudioSessionController:
    def __init__(self, audio_driver: Driver):
        self.driver = audio_driver
        self.active_task: Optional[asyncio.Task[None]] = None

    def cancel_active(self) -> None:
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            self.active_task = None

    async def fade_out(self, duration: float = FADE_DURATION) -> None:
        await asyncio.to_thread(self.driver.fade_out_dom, duration)
        await asyncio.sleep(duration)

    async def _ambient_lifecycle(self) -> None:
        try:
            print("[Audio] Ambient cue started. Playing naturally until track ends or manually faded.")
            await asyncio.to_thread(self.driver.play_category, False)
        except asyncio.CancelledError:
            pass

    async def _combat_lifecycle(self) -> None:
        try:
            await asyncio.to_thread(self.driver.pause_media)
            await asyncio.to_thread(self.driver.set_volume, 1.0)

            print(f"[Audio] Combat drop. Holding {COMBAT_PRE_ROLL_SILENCE}s pre-roll silence.")
            await asyncio.sleep(COMBAT_PRE_ROLL_SILENCE)

            print("[Audio] Combat cue firing. Playing naturally until track ends or manually faded.")
            await asyncio.to_thread(self.driver.play_category, True)
        except asyncio.CancelledError:
            pass

    async def _combat_resolved_lifecycle(self) -> None:
        try:
            print("[Audio] Combat resolved. Fading track.")
            await self.fade_out()
            print(f"[Audio] Entering post-combat cooldown silence ({POST_COMBAT_COOLDOWN}s).")
            await asyncio.sleep(POST_COMBAT_COOLDOWN)
            print("[Audio] Cooldown elapsed. Firing ambient exposition track.")
            await self._ambient_lifecycle()
        except asyncio.CancelledError:
            pass

    def trigger_ambient(self) -> None:
        self.cancel_active()
        self.active_task = asyncio.create_task(self._ambient_lifecycle())

    def trigger_fade(self) -> None:
        self.cancel_active()
        self.active_task = asyncio.create_task(self.fade_out())

    def trigger_combat(self) -> None:
        self.cancel_active()
        self.active_task = asyncio.create_task(self._combat_lifecycle())

    def trigger_combat_end(self) -> None:
        self.cancel_active()
        self.active_task = asyncio.create_task(self._combat_resolved_lifecycle())

    def trigger_stop(self) -> None:
        self.cancel_active()
        self.driver.pause_media()
        self.driver.set_volume(1.0)


driver: Optional[Driver] = None
controller: Optional[AudioSessionController] = None


@APP.on_event("startup")
async def startup_event() -> None:
    global driver, controller
    print("[Startup] Initializing Selenium Driver and Session Controller...")
    driver = Driver()
    controller = AudioSessionController(driver)
    print("[Startup] System ready.")


@APP.get("/trigger/{state}", response_class=HTMLResponse)
async def http_trigger(state: str) -> HTMLResponse:
    state_clean = state.strip().lower()
    if controller:
        if state_clean == "ambient":
            controller.trigger_ambient()
        elif state_clean == "fade":
            controller.trigger_fade()
        elif state_clean == "combat":
            controller.trigger_combat()
        elif state_clean == "combat_end":
            controller.trigger_combat_end()
        elif state_clean == "stop":
            controller.trigger_stop()

    return HTMLResponse(content=f"""
        <html>
        <head>
            <script>
                if (window.opener || window.history.length <= 1) {{
                    window.close();
                }} else {{
                    window.history.back();
                }}
            </script>
        </head>
        <body style="background:#181818;color:#aaa;font-family:monospace;text-align:center;padding:25px;">
            Triggered <b>{state_clean}</b>... returning.
        </body>
        </html>
    """)


@APP.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            msg = message.strip()
            if not controller:
                continue
            if msg == "combat_start":
                controller.trigger_combat()
            elif msg == "combat_end":
                controller.trigger_combat_end()
            elif msg == "fade":
                controller.trigger_fade()
            elif msg == "stop":
                controller.trigger_stop()
            else:
                controller.trigger_ambient()
    except WebSocketDisconnect:
        print("Websocket disconnected")
    finally:
        print("Websocket closed")


if __name__ == "__main__":
    import uvicorn

    try:
        print(f"Starting server on 127.0.0.1:{PORT}...")
        uvicorn.run("websocket_server:APP", host="127.0.0.1", port=PORT, log_level="info")
    except Exception:
        print("Fatal error starting server:")
        traceback.print_exc()
        sys.exit(1)