import matplotlib.pyplot as plt
import os

# Get the directory path of the current script
current_file_path = os.path.realpath(__file__)
directory_path = os.path.dirname(current_file_path)

# Function to parse the log file and extract Average Game Values
def parse_log(log_file, property):
    avg_game_values = []

    with open(log_file, 'r') as file:
        lines = file.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(property):
            avg_game_values.append(float(line.split(":")[1].strip()))
        i += 1

    return avg_game_values

# Main function to plot the graph
def main():
    log_file = f'{directory_path}/logs/mod_leduc_mccfr.log'  # Specify the name of your log file
    property = "Average game valueA:"
    property = "Avg regretB:"
    avg_game_values = parse_log(log_file, property)
    is_log_scale = False

    # Create a list of iteration numbers
    iterations = list(range(1, len(avg_game_values) + 1))

    # Plot the graph without markers
    scale = 'log' if is_log_scale else 'linear'
    plt.plot(iterations, avg_game_values, linestyle='-', color='b')
    plt.xscale(scale)
    plt.xlabel(f'Iteration ({scale} Scale)')
    plt.ylabel(property)
    plt.title(f'{property} vs. Iteration ({scale} Scale)')
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    main()
