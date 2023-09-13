import React from 'react';
import './styles.css';

const Cards = ({ cards = [], height = 60 }) => {
    const suit_symbol = {
        "h": "♥",
        "d": "♦",
        "c": "♣",
        "s": "♠"
    }

    const getSuit = (card) => {
        return card[card.length - 1]
    }

    const getValue = (card) => {
        return card.slice(0, card.length - 1)
    }

    const formatValue = (value) => {
        if (value === "T") {
            return "10"
        }
        return value
    }

    const getStyle = (card) => {
        const suit = getSuit(card)
        const defaultStyle = { width: `${height * 0.71}px`, height: `${height}px`, fontSize: `${height * 0.35}px` }
        if (suit === "h" || suit === "d") {
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
                        style={{ ...getStyle(card) }}

                    >
                        {formatValue(getValue(card))} {suit_symbol[getSuit(card)]}
                    </div>
                ))
            }
        </div >
    );
}

export default Cards;
