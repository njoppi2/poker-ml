import React from 'react';
import './styles.css';
import Players from '../Players';
import Cards from '../Cards';
import Slider from '../Slider';

const Game = ({ gameData }) => {
    if (!gameData || Object.keys(gameData).length === 0) {
        console.log('gameDatagameDatagameData: ', gameData)
        return <p>no data yet</p>
    } else {
        const humanPlayer = gameData.players.initial_players.find(p => p.is_robot === false);
        console.log('gameData: ', gameData);
        console.log('game data Object.keys', Object.keys(gameData));
        return (
            <div className='main'>
                <div className="table-outer-wrapper">
                    <p className='phase'>{gameData.phase_name}</p>
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
                    <div className="action-wrapper">
                        <div className="choices-wrapper">
                            <div className="choice">Fold</div>
                            <div className="choice">Check</div>
                            <div className="choice">Bet</div>
                        </div>
                        <Slider min={50} max={250} />
                    </div>
                </div>
            </div>
        );
    }
}

export default Game;


