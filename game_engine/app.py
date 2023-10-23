import asyncio
import websockets
import json
from main import simulate_poker_game


async def game_server(websocket, path):

    if path == "/points":
        # Handle WebSocket connections here
        try:
            # Send a JSON message to indicate the game has started
            json_message = json.dumps({"message": "Game started!"})
            await websocket.send(json_message)

            game_data = {"score": 42}
            while True:
                # Simulate game updates (replace with your game logic)
                await websocket.send(json.dumps(game_data))
                game_data["score"] += 1
                await asyncio.sleep(1)  # Send updates every 1 second

        except websockets.exceptions.ConnectionClosedOK:
            print("Client disconnected")

    elif path == "/start-game":
                # Handle WebSocket connections here
        try:
            await simulate_poker_game(websocket)
            #delete ↓
            json_message = json.dumps({"message": "Game started!"})
            await websocket.send(json_message)

        except websockets.exceptions.ConnectionClosedOK:
            print("Client disconnected")



start_server = websockets.serve(game_server, "localhost", 3002)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()