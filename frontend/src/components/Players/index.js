import { useState } from "react";

import Cards from "../Cards";
import "./styles.css";

const PLAYER_POSITIONS = [
  { top: "calc(50% - 45px)", left: "calc(4% + 10px)" },
  { top: "20px", left: "calc(30% - 45px)" },
  { top: "20px", left: "calc(50% - 45px)" },
  { top: "20px", left: "calc(70% - 45px)" },
  { top: "calc(50% - 45px)", right: "calc(4% + 10px)" },
  { bottom: "calc(4% + 10px)", left: "calc(70% - 45px)" },
  { bottom: "calc(4% + 10px)", left: "calc(50% - 45px)" },
  { bottom: "calc(4% + 10px)", left: "calc(30% - 45px)" },
];

const PLAYER_STATE_MESSAGES = {
  ALL_IN: "All In",
  FOLDED: "Folded",
  NOT_PLAYING: "Not Playing",
  PLAYING_TURN: "Playing",
  WAITING_FOR_TURN: "Waiting",
};

const PLAYER_STATE_STYLES = {
  ALL_IN: { boxShadow: "0 0 0 5px rgba(255, 255, 0, 0.7)", opacity: "0.8" },
  FOLDED: { opacity: "0.5", backgroundColor: "rgba(0, 42, 6)" },
  NOT_PLAYING: { visibility: "hidden" },
  PLAYING_TURN: { boxShadow: "0 0 0 5px rgba(255, 255, 255, 0.7)" },
  WAITING_FOR_TURN: {},
};

const Players = ({ players }) => {
  const [isCardVisible, setIsCardVisible] = useState(false);
  const initialPlayers = players?.initial_players || [];

  return (
    <>
      {initialPlayers.map((player, index) => (
        <div
          className="player-container"
          key={player.id}
          style={{ ...PLAYER_POSITIONS[index], ...PLAYER_STATE_STYLES[player.turn_state] }}
        >
          <div>{player.name}</div>
          <div className="money">{player.chips}</div>
          <div>{PLAYER_STATE_MESSAGES[player.turn_state]}</div>
          <div>Bet: {player.phase_bet_value}</div>
          {isCardVisible && player.is_robot ? (
            <div className="cards">
              <Cards cards={player.cards} height={30} />
            </div>
          ) : null}
          {player.is_robot ? (
            <button
              className="ai-player-toggle-cards"
              onClick={() => setIsCardVisible((previousValue) => !previousValue)}
              type="button"
            >
              Cards
            </button>
          ) : null}
        </div>
      ))}
    </>
  );
};

export default Players;
