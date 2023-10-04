import React from 'react';
import './styles.css';
import Cards from '../Cards';

const Player = ({ players }) => {
    const initial_players = players?.initial_players || [];
    const playerPosition = [
        { top: 'calc(50% - 45px)', left: `calc(4% + 10px)` },
        { top: '20px', left: `calc(30% - 45px)` },
        { top: '20px', left: `calc(50% - 45px)` },
        { top: '20px', left: `calc(70% - 45px)` },
        { top: 'calc(50% - 45px)', right: `calc(4% + 10px)` },
        { bottom: 'calc(4% + 10px)', left: `calc(70% - 45px)` },
        { bottom: 'calc(4% + 10px)', left: `calc(50% - 45px)` },
        { bottom: 'calc(4% + 10px)', left: `calc(30% - 45px)` },
    ]

    const playerStateMessage = {
        "NOT_PLAYING": "Not Playing",
        "WAITING_FOR_TURN": "Waiting",
        "PLAYING_TURN": "Playing",
        "FOLDED": "Folded",
        "ALL_IN": "All In"
    }

    const playerStateStyle = {
        "NOT_PLAYING": { visibility: "hidden" },
        "WAITING_FOR_TURN": {},
        "PLAYING_TURN": {
            boxShadow: "0 0 0 5px rgba(255, 255, 255, 0.7)"
        },
        "FOLDED": { opacity: "0.5", backgroundColor: "rgba(0, 42, 6)" },
        "ALL_IN": {
            boxShadow: "0 0 0 5px rgba(255, 255, 0, 0.7)", opacity: "0.8"
        }
    }

    return (
        <>
            {
                initial_players.map((player, index) => (
                    <div
                        className='player-container'
                        key={index}
                        style={{ ...playerPosition[index], ...playerStateStyle[player.turn_state] }}
                    >
                        {/* Render content for each player here */}
                        <div>{player.name}</div>
                        <div className='money'>{player.chips}</div>
                        <div>{playerStateMessage[player.turn_state]}</div>
                        <div>Bet: {player.phase_bet_value}</div>
                        {/* Add other player-related information */}
                        <div className='cards' style={player.is_robot ? {} : { display: 'None' }}>
                            <Cards cards={player.cards} height={30} />
                        </div>
                    </div>
                ))
            }
        </ >
    );
}

export default Player;
