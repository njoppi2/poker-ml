import React from 'react';
import './styles.css';

const OptionButton = ({ currentOption, setCurrentOption, myOption }) => {

    return (
        <div className='graph-option' style={currentOption == myOption ? { border: '3px solid #1d1a1a', opacity: '1', pointerEvents: 'none' } : {}} onClick={() => setCurrentOption(myOption)}>
            {myOption}
        </div>
    );
};

export default OptionButton;
