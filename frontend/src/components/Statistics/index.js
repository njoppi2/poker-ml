import { useState } from "react";

import Graph from "../Graph";
import OptionButton from "../OptionButton";
import "./styles.css";

function cumulativeSum(numbers) {
  let runningTotal = 0;
  return numbers.map((value) => {
    runningTotal += value;
    return runningTotal;
  });
}

function getData(data, graphOption) {
  if (graphOption === "Chips won per game") {
    return data;
  }
  return cumulativeSum(data);
}

const Statistics = ({ closePanel, gameData }) => {
  const initialPlayers = gameData.players?.initial_players || [];
  const [graphOption, setGraphOption] = useState("Chips won per game");
  const humanPlayer = initialPlayers.find((player) => player.is_robot === false);
  const chartData = getData(humanPlayer?.chips_won_history || [], graphOption);

  return (
    <div className="statistics-panel-wrapper">
      <button className="close-button" onClick={closePanel} type="button" />
      <div className="statistics-numbers-wrapper">
        <div className="statistics-numbers">
          <div className="number-row bold">Round:</div>
          <div className="number-row">{gameData.round_num}</div>
        </div>
        <div className="statistics-numbers">
          <div className="number-row bold">Total chip balance:</div>
          {initialPlayers.map((player) => (
            <div className="number-row" key={player.id}>
              <div className="number-column">{player.name.replace(/\d/g, "")}</div>
              <div className="number-column">{player.chip_balance}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="statistics-graphs-wrapper">
        <div className="statistics-graphs-header">
          <div className="graphs-header-text">Player statistics</div>
          <OptionButton
            currentOption={graphOption}
            myOption="Chips won per game"
            setCurrentOption={setGraphOption}
          />
          <OptionButton
            currentOption={graphOption}
            myOption="Total chip balance"
            setCurrentOption={setGraphOption}
          />
        </div>
        <div className="graph_wrapper">
          <Graph data={chartData} />
        </div>
      </div>
    </div>
  );
};

export default Statistics;
