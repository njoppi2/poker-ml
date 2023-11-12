import React, { useState } from 'react';
import './styles.css';
import Cards from '../Cards';
import Graph from '../Graph';
import OptionButton from '../OptionButton';

function cumulativeSum(numbers) {
    if (!Array.isArray(numbers)) {
        throw new Error('Input must be an array of numbers');
    }

    return numbers.map((_, index) => numbers.slice(0, index + 1).reduce((sum, num) => sum + num, 0));
}

function getData(data, graphOption) {
    if (graphOption === "Chips won per game") {
        return data
    } else {
        return cumulativeSum(data)
    }
}

const Statistics = ({ gameData, closePanel }) => {
    const initial_players = gameData.players?.initial_players || [];
    const [graphOption, setGraphOption] = useState("Chips won per game");

    const humanPlayer = initial_players.find(p => p.is_robot === false);
    return (
        <div className='statistics-panel-wrapper'>
            <div className='close-button' onClick={closePanel} />
            <div className='statistics-numbers-wrapper'>
                <div className='statistics-numbers'>
                    <div className='number-row bold'>Round:</div>
                    <div className='number-row'>{gameData.round_num}</div>
                </div>
                <div className='statistics-numbers'>
                    <div className='number-row bold'>Total chip balance:</div>
                    {
                        initial_players.map((player, index) => (
                            <div
                                className='number-row'
                                key={index}
                            >
                                <div className='number-column'>{player.name.replace(/\d/g, '')}</div>
                                <div className='number-column'>{player.chip_balance}</div>
                            </div>
                        ))
                    }
                </div>
            </div>
            <div className='statistics-graphs-wrapper'>
                <div className='statistics-graphs-header'>
                    <div className='graphs-header-text'>Player statistics</div>
                    <OptionButton currentOption={graphOption} setCurrentOption={(type) => setGraphOption(type)} myOption={"Chips won per game"} />
                    <OptionButton currentOption={graphOption} setCurrentOption={(type) => setGraphOption(type)} myOption={"Total chip balance"} />
                </div>
                <div className='graph_wrapper'>
                    <Graph data={getData(humanPlayer.chip_balance_history, graphOption)} />
                </div>
            </div>
        </div >
    );
}

export default Statistics;
