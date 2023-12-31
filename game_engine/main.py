from game import Game
import asyncio
import websockets

# Define your game simulation function
async def simulate_poker_game(websocket, game_type):
    game = Game(websocket=websocket, game_type=game_type, num_ai_players=1, num_human_players=1, initial_chips=1200, increase_blind_every=0)
    await game.start_game()

# WebSocket connection handler
async def handle_client(websocket, path):
    async for message in websocket:
        # The frontend has sent the "start-game" message, so we start the poker game simulation
        if message == "start-game-Texas Hold'em":
            await simulate_poker_game(websocket, "Texas Hold'em")
        elif message == "start-game-Leduc":
            await simulate_poker_game(websocket, "Leduc")
        break  # Exit the loop after the game is started


# Run the poker game simulation
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--no-websocket":
        # Run the game simulation without WebSocket
        asyncio.run(simulate_poker_game())
    else:
        # Start the WebSocket server
        import asyncio

        # Create an asyncio event loop
        loop = asyncio.get_event_loop()

        # Start the WebSocket server
        start_server = websockets.serve(handle_client, "0.0.0.0", 3002)

        # Run the server within the event loop
        loop.run_until_complete(start_server)
        loop.run_forever()
