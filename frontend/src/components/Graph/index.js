const CHART_HEIGHT = 220;
const CHART_WIDTH = 520;
const BASELINE = CHART_HEIGHT / 2;

const Graph = ({ data }) => {
  if (!data.length) {
    return <div className="empty-chart">No round history yet.</div>;
  }

  const maxMagnitude = Math.max(...data.map((value) => Math.abs(value)), 1);
  const barWidth = CHART_WIDTH / data.length;

  return (
    <svg className="chart" viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} role="img">
      <line
        stroke="rgba(19, 41, 30, 0.3)"
        strokeWidth="2"
        x1="0"
        x2={CHART_WIDTH}
        y1={BASELINE}
        y2={BASELINE}
      />
      {data.map((value, index) => {
        const normalizedHeight = (Math.abs(value) / maxMagnitude) * (CHART_HEIGHT / 2 - 16);
        const x = index * barWidth + 8;
        const y = value >= 0 ? BASELINE - normalizedHeight : BASELINE;

        return (
          <rect
            fill={value >= 0 ? "#0f9d58" : "#d54f4f"}
            height={normalizedHeight}
            key={`${index}-${value}`}
            rx="6"
            width={Math.max(barWidth - 14, 8)}
            x={x}
            y={y}
          />
        );
      })}
    </svg>
  );
};

export default Graph;
