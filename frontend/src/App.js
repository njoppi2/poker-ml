import { useState } from "react";

import Game from "./components/Game";
import OptionButton from "./components/OptionButton";
import { usePokerSession } from "./hooks/usePokerSession";
import "./App.css";

const GAME_OPTIONS = ["Texas Hold'em", "Leduc"];
const CHIP_MODE_OPTIONS = [
  { label: "Persistent Match", value: "persistent_match" },
  { label: "Reset Each Round", value: "reset_each_round" },
];

function App() {
  const [gameType, setGameType] = useState("Leduc");
  const [chipMode, setChipMode] = useState("persistent_match");
  const [sessionAttempt, setSessionAttempt] = useState(0);
  const [isChipSpinning, setIsChipSpinning] = useState(false);

  const sessionRequest =
    sessionAttempt === 0
      ? null
      : {
          chipMode,
          gameType,
          sessionKey: `${gameType}:${chipMode}:${sessionAttempt}`,
        };

  const { connectionState, errorMessage, gameData, sendMessage, sessionMode } = usePokerSession(
    sessionRequest,
  );

  const startGame = () => {
    setIsChipSpinning(true);
    window.setTimeout(() => {
      setSessionAttempt((currentAttempt) => currentAttempt + 1);
    }, 900);
  };

  const chipModeLabel = CHIP_MODE_OPTIONS.find((option) => option.value === chipMode)?.label;
  const showLobby = gameData === null;
  const statusMessage =
    connectionState === "connecting"
      ? "Connecting to backend..."
      : connectionState === "mock"
        ? "Backend not reachable. Falling back to playable mock mode."
      : connectionState === "streaming"
        ? sessionMode === "mock"
          ? "Mock mode active."
          : "Game state received."
        : connectionState === "closed"
          ? "Connection closed."
          : errorMessage;

  return (
    <div className="App">
      {showLobby ? (
        <div className="initial-page">
          <div className="panel-header">
            <div className="eyebrow">Poker ML</div>
            <h1>Choose your match</h1>
            <p>Local play works automatically. Set `VITE_WS_URL` only if you need a custom websocket endpoint.</p>
          </div>
          <div className="option-group">
            <div className="group-label">Game</div>
            <div className="options-wrapper">
              {GAME_OPTIONS.map((option) => (
                <OptionButton
                  key={option}
                  currentOption={gameType}
                  myOption={option}
                  setCurrentOption={setGameType}
                />
              ))}
            </div>
          </div>
          <div className="option-group">
            <div className="group-label">Chip mode</div>
            <div className="options-wrapper">
              {CHIP_MODE_OPTIONS.map((option) => (
                <OptionButton
                  key={option.value}
                  currentOption={chipMode}
                  myOption={option.value}
                  setCurrentOption={setChipMode}
                >
                  {option.label}
                </OptionButton>
              ))}
            </div>
          </div>
          <div className="session-summary">
            {gameType} · {chipModeLabel}
          </div>
          <button className="start-button" onClick={startGame} type="button">
            {sessionAttempt === 0 ? "Start Game" : "Restart Session"}
          </button>
          <div className={`status-message ${connectionState === "error" ? "error" : ""}`}>
            {statusMessage || "Choose a mode and start a session."}
          </div>
        </div>
      ) : (
        <Game gameData={gameData} onRestart={startGame} sendMessage={sendMessage} />
      )}
      <div className="App-logo" style={!isChipSpinning ? { animation: "none" } : {}} />
    </div>
  );
}

export default App;
