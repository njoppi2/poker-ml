from game import Game
import asyncio


# Define your game simulation function
async def simulate_poker_game(websocket=None):

    game = Game(websocket=websocket, num_ai_players=3, num_human_players=1, initial_chips=1000, increase_blind_every=10)
    await game.start_game()
        
                
# Run the poker game simulation
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--no-websocket":
        # Run the game simulation without WebSocket
        asyncio.run(simulate_poker_game())
    else:
        # Start the WebSocket server
        import asyncio
        import websockets

        async def handle_client(websocket, path):
            await simulate_poker_game(websocket)

        # Create an asyncio event loop
        loop = asyncio.get_event_loop()

        # Start the WebSocket server
        start_server = websockets.serve(handle_client, "localhost", 3002)

        # Run the server within the event loop
        loop.run_until_complete(start_server)
        loop.run_forever()
