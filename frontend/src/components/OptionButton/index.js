import "./styles.css";

const OptionButton = ({ children, currentOption, myOption, setCurrentOption }) => {
  const isSelected = currentOption === myOption;

  return (
    <button
      className={`graph-option ${isSelected ? "selected" : ""}`}
      onClick={() => setCurrentOption(myOption)}
      type="button"
    >
      {children || myOption}
    </button>
  );
};

export default OptionButton;
