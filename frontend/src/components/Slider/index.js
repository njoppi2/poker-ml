import "./styles.css";

export default function InputSlider({ min, max, value, onValueChange }) {
  const clampedMin = Math.min(min, max);

  const handleSliderChange = (event) => {
    onValueChange(Number(event.target.value));
  };

  const handleInputChange = (event) => {
    if (event.target.value === "") {
      onValueChange(clampedMin);
      return;
    }

    onValueChange(Number(event.target.value));
  };

  const handleBlur = () => {
    if (value < clampedMin) {
      onValueChange(clampedMin);
    } else if (value > max) {
      onValueChange(max);
    }
  };

  return (
    <div className="slider-container">
      <input
        aria-label="Bet size"
        className="slider-range"
        max={max}
        min={clampedMin}
        onChange={handleSliderChange}
        type="range"
        value={value}
      />
      <input
        className="slider-input"
        max={max}
        min={clampedMin}
        onBlur={handleBlur}
        onChange={handleInputChange}
        type="number"
        value={value}
      />
    </div>
  );
}
