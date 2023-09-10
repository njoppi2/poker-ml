import React from 'react';
import './styles.css';

const Cards = ({ cards = [], height = 60 }) => {
    const suit_symbol = {
        "Hearts": "♥",
        "Diamonds": "♦",
        "Clubs": "♣",
        "Spades": "♠"
    }

    const getStyle = (suit) => {
        const defaultStyle = { width: `${height * 0.71}px`, height: `${height}px`, fontSize: `${height * 0.35}px` }
        if (suit === "Hearts" || suit === "Diamonds") {
            return { ...defaultStyle, color: "red" }
        } else {
            return { ...defaultStyle, color: "black" }
        }
    }

    return (
        <div className='cards-container'>
            {
                cards.map((card, index) => (
                    <div
                        className='card'
                        key={index}
                        style={{ ...getStyle(card.suit) }}

                    >
                        {card.value} {suit_symbol[card.suit]}
                    </div>
                ))
            }
        </div >
    );
}

export default Cards;
