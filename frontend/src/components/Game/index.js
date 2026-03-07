import { Suspense, lazy, useEffect, useState } from "react";

import Cards from "../Cards";
import Players from "../Players";
import Slider from "../Slider";
import "./styles.css";

const Statistics = lazy(() => import("../Statistics"));

const CHIP_MODE_LABELS = {
  persistent_match: "Persistent match",
  reset_each_round: "Reset each round",
};

const Game = ({ gameData, onRestart, sendMessage }) => {
  const humanPlayer = gameData.players.initial_players.find((player) => player.is_robot === false);
  const [sliderValue, setSliderValue] = useState(0);
  const [isStatisticsPanelOpen, setStatisticsPanelOpen] = useState(false);

  const minTurnValue = gameData.min_turn_value_to_continue ?? 0;
  const minimumRaise = humanPlayer
    ? Math.min(Math.max(gameData.min_bet, minTurnValue * 2 || gameData.min_bet), humanPlayer.chips)
    : 0;

  useEffect(() => {
    setSliderValue(minimumRaise);
  }, [minimumRaise]);

  if (!humanPlayer) {
    return null;
  }

  return (
    <div className="main">
      <button
        className="statistics-button"
        onClick={() => setStatisticsPanelOpen((previousValue) => !previousValue)}
        type="button"
      />
      {isStatisticsPanelOpen ? (
        <Suspense fallback={<div className="panel-loading">Loading statistics...</div>}>
          <Statistics gameData={gameData} closePanel={() => setStatisticsPanelOpen(false)} />
        </Suspense>
      ) : null}
      <div className="table-outer-wrapper">
        <div className="table-wrapper">
          <div className="table">
            <div className="table-meta">
              <div className="meta-pill">{gameData.game_type}</div>
              <div className="meta-pill">{CHIP_MODE_LABELS[gameData.chip_mode]}</div>
              {gameData.phase_name ? <div className="meta-pill">{gameData.phase_name}</div> : null}
            </div>
            <div className="table-cards-wrapper">
              <Cards cards={gameData.table_cards} />
            </div>
            <div className="pot">Pot: {gameData.total_pot}</div>
            <Players players={gameData.players} />
          </div>
        </div>
      </div>
      <div className="buttons-wrapper">
        <div className="hand">
          <Cards cards={humanPlayer.cards} height={100} />
        </div>
        {humanPlayer.turn_state === "PLAYING_TURN" && !gameData.game_over ? (
          <div className="action-wrapper">
            <div className="choices-wrapper">
              {minTurnValue !== 0 ? (
                <button className="choice" onClick={() => sendMessage("Fold")} type="button">
                  Fold
                </button>
              ) : null}
              {minTurnValue === 0 ? (
                <button className="choice" onClick={() => sendMessage("Check")} type="button">
                  Check
                </button>
              ) : null}
              {minTurnValue !== 0 ? (
                <button className="choice" onClick={() => sendMessage("Call")} type="button">
                  Call
                </button>
              ) : null}
              {minTurnValue < humanPlayer.chips ? (
                <button
                  className="choice"
                  onClick={() => sendMessage(`Bet ${sliderValue}`)}
                  type="button"
                >
                  Bet
                </button>
              ) : null}
            </div>
            {minimumRaise > 0 ? (
              <Slider
                min={minimumRaise}
                max={humanPlayer.chips}
                onValueChange={setSliderValue}
                value={sliderValue}
              />
            ) : null}
          </div>
        ) : null}
        {gameData.game_over ? (
          <div className="game-status-banner">
            <div>{gameData.winner_name ? `${gameData.winner_name} wins` : "Match complete"}</div>
            <button className="choice restart" onClick={onRestart} type="button">
              Play Again
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default Game;
