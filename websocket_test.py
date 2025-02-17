"""
Send a message to the websocket server.
"""

import asyncio
import random

import websockets

from websocket_server import PORT


async def test_websocket():
    uri = f"ws://127.0.0.1:{PORT}/ws"
    async with websockets.connect(uri) as websocket:
        choice = random.choice(["combat_start", "combat_end"])
        print(choice)
        await websocket.send(choice)


asyncio.run(test_websocket())
