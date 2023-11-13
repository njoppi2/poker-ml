import React, { useState, useEffect } from 'react';
import './styles.css';
import Players from '../Players';
import Statistics from '../Statistics';
import Cards from '../Cards';
import Slider from '../Slider';


const Game = ({ gameData, sendMessage }) => {
    const humanPlayer = gameData.players.initial_players.find(p => p.is_robot === false);
    const minBetOrRaise = Math.min(2 * gameData.min_turn_value_to_continue || gameData.min_bet, humanPlayer.chips);
    const [min, setMin] = useState(gameData.min_turn_value_to_continue);
    const [minBet, setMinBet] = useState(minBetOrRaise);
    const [sliderValue, setSliderValue] = useState(minBetOrRaise);
    const [isStatisticsPanelOpen, setStatisticsPanelOpen] = useState(false);
    console.log('gameData: ', gameData);

    useEffect(() => {
        setMin(gameData.min_turn_value_to_continue);
        setMinBet(minBetOrRaise);
        setSliderValue(minBetOrRaise);
    }, [gameData.min_turn_value_to_continue, gameData.min_bet, humanPlayer.chips]);

    return (
        <div className='main'>
            <div className='statistics-button' onClick={() => setStatisticsPanelOpen(prev => !prev)} />
            {isStatisticsPanelOpen && <Statistics gameData={gameData} closePanel={() => setStatisticsPanelOpen()} />}
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
                        {min !== 0 && <div className="choice" onClick={() => sendMessage("Fold")}>Fold</div>}
                        {min === 0 && <div className="choice" onClick={() => sendMessage("Check")}>Check</div>}
                        {min !== 0 && <div className="choice" onClick={() => sendMessage("Call")}>Call</div>}
                        {min < humanPlayer.chips && <div className="choice" onClick={() => sendMessage("Bet " + sliderValue)}>Bet</div>}
                    </div>
                    <Slider min={minBetOrRaise} max={humanPlayer.chips} value={sliderValue} onValueChange={setSliderValue} />
                </div>}
            </div>
        </div >
    );
}

export default Game;


