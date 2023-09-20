import React, { useEffect, useState } from 'react';
import Game from './components/Game';

function App() {
    const [gameData, setGameData] = useState({});
    const [socket, setSocket] = useState(null); // WebSocket connection state
    const [initialPage, setInitialPage] = useState(true); // WebSocket connection state

    const sendMessage = (message) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(message);
        }
    };

    const handleInitialPageClick = () => {
        setInitialPage(false);
    }

    useEffect(() => {
        if (initialPage) return;
        const newSocket = new WebSocket('ws://localhost:3002'); // Replace with your WebSocket server URL

        newSocket.onopen = () => {
            console.log('WebSocket connected');
            // Send a message to start the game on the server
            newSocket.send('start-game');
        };

        newSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received game update:', data);
            // Update your game UI or state with the received data
            setGameData(data);
        };

        newSocket.onclose = () => {
            console.log('WebSocket disconnected');
        };

        // Store the WebSocket connection in state
        setSocket(newSocket);

        return () => {
            // Clean up the WebSocket connection when the component unmounts
            if (newSocket.readyState === 1) {
                newSocket.close();
            }
        };
    }, [initialPage]);

    return (
        <div className="App">
            {initialPage ? (
                <div className="initial-page" onClick={handleInitialPageClick}>
                    Start the game!
                </div>
            ) : (
                (!gameData || Object.keys(gameData).length === 0) ? (
                    <p>Loading</p>
                ) : (
                    <Game gameData={gameData} sendMessage={sendMessage} />
                )
            )
            }
        </div>
    );
}

export default App;
