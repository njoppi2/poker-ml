import { useEffect, useRef, useState } from "react";

import { createMockPokerSession } from "../lib/mockSession";
import { buildStartGameMessage, resolveWebSocketUrl } from "../lib/socket";

const SOCKET_STATES = {
  CLOSED: 3,
  CONNECTING: 0,
  OPEN: 1,
};

const FALLBACK_TO_MOCK_MESSAGE =
  "Backend unavailable. Running in frontend mock mode so the game stays playable.";
const CONNECTION_ERROR_MESSAGE = "Could not establish a websocket session.";
const PAYLOAD_ERROR_MESSAGE = "The backend returned invalid game data.";

export function usePokerSession(sessionRequest) {
  const socketRef = useRef(null);
  const mockSessionRef = useRef(null);
  const [gameData, setGameData] = useState(null);
  const [connectionState, setConnectionState] = useState("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [sessionMode, setSessionMode] = useState("none");
  const sessionKey = sessionRequest?.sessionKey;
  const gameType = sessionRequest?.gameType;
  const chipMode = sessionRequest?.chipMode;

  useEffect(() => {
    if (!sessionKey || !gameType || !chipMode) {
      return undefined;
    }

    let socket = null;
    let hasReceivedBackendPayload = false;
    let fallbackTriggered = false;
    let isDisposed = false;

    const stopMockSession = () => {
      mockSessionRef.current?.stop();
      mockSessionRef.current = null;
    };

    const startMockSession = (message) => {
      if (fallbackTriggered || isDisposed) {
        return;
      }
      fallbackTriggered = true;

      if (
        socket &&
        (socket.readyState === SOCKET_STATES.OPEN || socket.readyState === SOCKET_STATES.CONNECTING)
      ) {
        socket.close();
      }

      stopMockSession();
      const mockSession = createMockPokerSession({
        chipMode,
        gameType,
        onUpdate: (payload) => {
          if (isDisposed) {
            return;
          }
          setGameData(payload);
          setConnectionState("streaming");
        },
      });
      mockSessionRef.current = mockSession;
      setSessionMode("mock");
      setConnectionState("mock");
      setErrorMessage(message);
      mockSession.start();
    };

    const websocketUrl = resolveWebSocketUrl();
    if (!websocketUrl) {
      setGameData(null);
      startMockSession(FALLBACK_TO_MOCK_MESSAGE);
      return () => {
        isDisposed = true;
        stopMockSession();
      };
    }

    setGameData(null);
    setConnectionState("connecting");
    setErrorMessage("");
    setSessionMode("backend");

    socket = new WebSocket(websocketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      if (isDisposed) {
        return;
      }
      setConnectionState("connected");
      socket.send(buildStartGameMessage(gameType, chipMode));
    };

    socket.onmessage = (event) => {
      if (isDisposed) {
        return;
      }
      try {
        hasReceivedBackendPayload = true;
        setGameData(JSON.parse(event.data));
        setConnectionState("streaming");
        setErrorMessage("");
      } catch {
        setConnectionState("error");
        setErrorMessage(PAYLOAD_ERROR_MESSAGE);
      }
    };

    socket.onerror = () => {
      if (isDisposed) {
        return;
      }
      if (!hasReceivedBackendPayload) {
        startMockSession(FALLBACK_TO_MOCK_MESSAGE);
        return;
      }
      setConnectionState("error");
      setErrorMessage(CONNECTION_ERROR_MESSAGE);
    };

    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      if (!hasReceivedBackendPayload) {
        startMockSession(FALLBACK_TO_MOCK_MESSAGE);
        return;
      }
      setConnectionState((currentState) => {
        if (currentState === "error" || currentState === "mock") {
          return currentState;
        }
        return "closed";
      });
    };

    return () => {
      isDisposed = true;
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      if (
        socket.readyState === SOCKET_STATES.OPEN ||
        socket.readyState === SOCKET_STATES.CONNECTING
      ) {
        socket.close();
      }
      stopMockSession();
    };
  }, [chipMode, gameType, sessionKey]);

  const sendMessage = (message) => {
    if (mockSessionRef.current) {
      mockSessionRef.current.sendMessage(message);
      return;
    }
    if (socketRef.current?.readyState === SOCKET_STATES.OPEN) {
      socketRef.current.send(message);
    }
  };

  return {
    connectionState,
    errorMessage,
    gameData,
    sessionMode,
    sendMessage,
  };
}
