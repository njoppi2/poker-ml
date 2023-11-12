// MyChart.js
import React from 'react';
import { VictoryBar, VictoryChart, VictoryAxis, VictoryTheme } from 'victory';

const MyChart = ({ data }) => {
    const chartData = data.map((value, index) => ({ x: index + 1, y: value }));
    const maxXValue = Math.max(data.length, 10);

    return (
        <VictoryChart theme={VictoryTheme.material} domain={{ x: [1, maxXValue] }}>
            <VictoryAxis />
            <VictoryAxis dependentAxis />
            <VictoryBar data={chartData} barWidth={(100 / maxXValue) + 1} />
        </VictoryChart>
    );
};

export default MyChart;
