import React, { useState, useEffect } from 'react';
import './styles.css';
import Players from '../Players';
import Cards from '../Cards';
import Slider from '../Slider';


const Game = ({ gameData, sendMessage }) => {
    const [min, setMin] = useState(gameData.min_turn_bet_to_continue);
    const [sliderValue, setSliderValue] = useState(min);
    const humanPlayer = gameData.players.initial_players.find(p => p.is_robot === false);
    console.log('gameData: ', gameData);

    useEffect(() => {
        setMin(gameData.min_turn_bet_to_continue);
        setSliderValue(gameData.min_turn_bet_to_continue);
    }, [gameData.min_turn_bet_to_continue]);

    return (
        <div className='main'>
            <div className="table-outer-wrapper">
                <div className="table-wrapper">
                    <div className="table">
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
                {humanPlayer.turn_state === "PLAYING_TURN" && <div className="action-wrapper">
                    < div className="choices-wrapper">
                        <div className="choice" onClick={() => sendMessage("Fold")}>Fold</div>
                        {min === 0 && <div className="choice" onClick={() => sendMessage("Check")}>Check</div>}
                        <div className="choice" onClick={() => sendMessage("Bet " + sliderValue)}>Bet</div>
                    </div>
                    <Slider min={min} max={humanPlayer.chips} value={sliderValue} onValueChange={setSliderValue} />
                </div>}
            </div>
        </div >
    );
}

export default Game;


