import { useEffect, useRef, useState } from "react";

import { buildStartGameMessage, resolveWebSocketUrl } from "../lib/socket";

const SOCKET_STATES = {
  CLOSED: 3,
  CONNECTING: 0,
  OPEN: 1,
};

const HOSTED_BACKEND_MESSAGE =
  "This frontend only auto-connects on localhost. Set VITE_WS_URL to point at a websocket server if needed.";
const CONNECTION_ERROR_MESSAGE =
  "Could not establish a websocket session. Start the backend locally or configure VITE_WS_URL.";
const PAYLOAD_ERROR_MESSAGE = "The backend returned invalid game data.";

export function usePokerSession(sessionRequest) {
  const socketRef = useRef(null);
  const [gameData, setGameData] = useState(null);
  const [connectionState, setConnectionState] = useState("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const sessionKey = sessionRequest?.sessionKey;
  const gameType = sessionRequest?.gameType;
  const chipMode = sessionRequest?.chipMode;

  useEffect(() => {
    if (!sessionKey || !gameType || !chipMode) {
      return undefined;
    }

    const websocketUrl = resolveWebSocketUrl();
    if (!websocketUrl) {
      setGameData(null);
      setConnectionState("error");
      setErrorMessage(HOSTED_BACKEND_MESSAGE);
      return undefined;
    }

    setGameData(null);
    setConnectionState("connecting");
    setErrorMessage("");

    const socket = new WebSocket(websocketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnectionState("connected");
      socket.send(buildStartGameMessage(gameType, chipMode));
    };

    socket.onmessage = (event) => {
      try {
        setGameData(JSON.parse(event.data));
        setConnectionState("streaming");
      } catch {
        setConnectionState("error");
        setErrorMessage(PAYLOAD_ERROR_MESSAGE);
      }
    };

    socket.onerror = () => {
      setConnectionState("error");
      setErrorMessage(CONNECTION_ERROR_MESSAGE);
    };

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      setConnectionState((currentState) => {
        if (currentState === "error") {
          return currentState;
        }
        return "closed";
      });
    };

    return () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      if (
        socket.readyState === SOCKET_STATES.OPEN ||
        socket.readyState === SOCKET_STATES.CONNECTING
      ) {
        socket.close();
      }
    };
  }, [chipMode, gameType, sessionKey]);

  const sendMessage = (message) => {
    if (socketRef.current?.readyState === SOCKET_STATES.OPEN) {
      socketRef.current.send(message);
    }
  };

  return {
    connectionState,
    errorMessage,
    gameData,
    sendMessage,
  };
}
