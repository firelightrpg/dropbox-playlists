"""
Send a message to the websocket server.
"""

import asyncio

import websockets

from websocket_server import PORT


async def test_websocket():
    uri = f"ws://127.0.0.1:{PORT}/ws"
    async with websockets.connect(uri) as websocket:
        await websocket.send("combat_end")  # Change to "combat_end" for testing


asyncio.run(test_websocket())
