import React, { useEffect, useState } from 'react';
import Game from './components/Game';

function App() {
    const [gameData, setGameData] = useState({});
    const [socket, setSocket] = useState(null); // WebSocket connection state

    useEffect(() => {
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
    }, []); // Empty dependency array to run the effect only once when the component mounts

    useEffect(() => {
    }, [gameData]); // Add gameData as a dependency

    return (
        <div className="App">
            <Game gameData={gameData} />
        </div>
    );
}

export default App;
