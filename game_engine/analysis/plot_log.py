import matplotlib.pyplot as plt

# Function to parse the log file and extract Average Game Values
def parse_log(log_file):
    avg_game_values = []

    with open(log_file, 'r') as file:
        lines = file.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("Average game value:"):
            avg_game_values.append(float(line.split(":")[1].strip()))
        i += 1

    return avg_game_values

# Main function to plot the graph
def main():
    log_file = 'logs/mccfr.log'  # Specify the name of your log file
    avg_game_values = parse_log(log_file)

    # Create a list of iteration numbers
    iterations = list(range(1, len(avg_game_values) + 1))

    # Plot the graph without markers
    plt.plot(iterations, avg_game_values, linestyle='-', color='b')
    plt.xscale('log')  # Set the X-axis to log scale
    plt.xlabel('Iteration (Log Scale)')
    plt.ylabel('Average Game Value')
    plt.title('Average Game Value vs. Iteration (Log Scale)')
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
