import sys
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
from scipy.stats import norm

# Get the directory path of the current script
current_file_path = os.path.realpath(__file__)
directory_path = os.path.dirname(current_file_path)
is_inverted_seat = False

def plot_histogram(rewards):
    plt.figure(figsize=(12, 6))
    # Create histogram with specified bins from -1200 to 1200 with a step of 100
    bins = range(-1250, 1250, 100)  # Goes to 1300 so that 1200 is included as the right edge for the last bin
    #counts, edges = np.histogram(rewards, bins=bins)
    plt.hist(rewards, bins=bins, edgecolor='black')

    plt.title('Histogram of Game Outcomes')
    plt.xlabel('Rewards')
    plt.ylabel('Number of Games')
    plt.grid(True)

    # Print the frequency of each category
    # for i in range(len(counts)):
    #     print(f'Rewards between {edges[i]} and {edges[i+1]}: {counts[i]}')

    plt.show()

def plot_gaussian(rewards):
    # Calculate the mean and standard deviation from the rewards
    mean = np.mean(rewards)
    std_dev = np.std(rewards)

    # Generate some data points within the range of rewards for plotting
    min_reward = min(rewards)
    max_reward = max(rewards)
    x = np.linspace(min_reward, max_reward, 1000)

    # Create a normal distribution with the calculated mean and standard deviation
    y = norm.pdf(x, mean, std_dev)

    plt.figure(figsize=(10, 6))
    plt.plot(x, y, label='Normal Distribution')

    plt.title('Gaussian Distribution of Rewards')
    plt.xlabel('Reward')
    plt.ylabel('Probability Density')
    plt.grid(True)
    plt.legend()

    plt.show()

def plot_statistics(rewards1, rewards2, rewards3):
    # Convert rewards to pandas Series for cumulative sum
    rewards_series1 = pd.Series(rewards1).cumsum()
    rewards_series2 = pd.Series(rewards2).cumsum()
    rewards_series3 = pd.Series(rewards3).cumsum()


    # Plot the bankroll over time for both series
    plt.figure(figsize=(12, 6))

    # Plot each series on the same figure
    rewards_series1.plot(label='Rewards 1', color='blue')
    rewards_series2.plot(label='Rewards 2', color='orange')
    rewards_series3.plot(label='Rewards 3', color='green')


    # Title and labels
    plt.title('Bankroll Over Time')
    plt.xlabel('Game Number')
    plt.ylabel('Bankroll')

    # Show grid and legend
    plt.grid(True)
    plt.legend()

    # Display the plot
    plt.show()

def get_hand_quality_proportion(matchlist):
    CARDS_RANK = {'Q': 0, 'K': 1, 'A': 2, 'Pair': 3}
    p1_should_win = []
    p1_should_draw = []
    p1_should_lose = []

    for line in matchlist:
        parts = line.split(':')
        cards = parts[3].split('/')

        if int(parts[1]) % 2 == 0:
            p1_card = cards[0].split('|')[0]
            p2_card = cards[0].split('|')[1]
        else:
            p1_card = cards[0].split('|')[1]
            p2_card = cards[0].split('|')[0]

        p1_card = ''.join(filter(str.isupper, p1_card))
        p2_card = ''.join(filter(str.isupper, p2_card))

        if len(cards) > 1:
            common_card = ''.join(filter(str.isupper, cards[1]))
            if (p1_card == common_card):
                p1_rank = 3
            else:
                p1_rank = CARDS_RANK[p1_card]

            if (p2_card == common_card):
                p2_rank = 3
            else:
                p2_rank = CARDS_RANK[p2_card]
        else:
            p1_rank = CARDS_RANK[p1_card]
            p2_rank = CARDS_RANK[p2_card]

        if (p1_rank > p2_rank):
            p1_should_win.append(line)
        elif (p1_rank == p2_rank):
            p1_should_draw.append(line)
        else:
            p1_should_lose.append(line)

    return p1_should_win, p1_should_draw, p1_should_lose

def analyze_log_file(log_file_path):
    # Vetores para armazenar as partidas ganhas, empatadas e perdidas pelo TCC_AI
    matches = []
    p1_wins = []
    p1_draws = []
    p1_losses = []
    p1_rewards = []

    #count_games = 0
    # Abrir o arquivo e ler linha por linha
    with open(log_file_path, 'r') as file:
        for line in file:
            # if count_games == 1000:
            #     break
            # Verificar se a linha começa com "STATE:"
            if line.startswith("STATE:"):
                #count_games += 1
                # Separar os componentes da linha
                parts = line.split(':')

                # Extrair o ganho do jogador TCC_AI, que pode estar na quinta ou sexta posição da linha,
                # dependendo de quem começou jogando a partida
                if int(parts[1]) % 2 == 0:
                    p1_gain = int(parts[4].split('|')[1])

                else:
                    p1_gain = int(parts[4].split('|')[0])

                # Adicionar o ganho do jogador TCC_AI ao vetor de recompensas
                if is_inverted_seat:
                    p1_gain = -int(p1_gain)
                else:
                    p1_gain = int(p1_gain)
                p1_rewards.append(int(p1_gain))

                # Classificar a partida como ganha, empatada ou perdida
                matches.append(line)
                if p1_gain > 0:
                    p1_wins.append(line)
                elif p1_gain == 0:
                    p1_draws.append(line)
                else:
                    p1_losses.append(line)

    # Calculate statistics
    total_games = len(p1_wins) + len(p1_draws) + len(p1_losses)
    win_rate = len(p1_wins) / total_games
    draw_rate = len(p1_draws) / total_games
    loss_rate = len(p1_losses) / total_games
    average_win_margin = np.mean([gain for gain in p1_rewards if gain > 0]) if p1_wins else 0
    average_loss_margin = np.mean([abs(gain) for gain in p1_rewards if gain < 0]) if p1_losses else 0
    std_deviation = np.std(p1_rewards)

    stats = {
        'total_games': total_games,
        'win_rate': win_rate,
        'draw_rate': draw_rate,
        'loss_rate': loss_rate,
        'average_win_margin': average_win_margin,
        'average_loss_margin': average_loss_margin,
        'std_deviation': std_deviation,
        'expected_value': win_rate * average_win_margin + loss_rate * average_loss_margin
    }

    return matches, p1_wins, p1_draws, p1_losses, p1_rewards, stats

def analyze_directory(directory_path):
    # Lists to store the results from all files
    all_matches = []
    all_p1_wins = []
    all_p1_draws = []
    all_p1_losses = []
    all_p1_rewards = []

    # Loop through each file in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith('.log'):  # Check if the file is a log file
            log_file_path = os.path.join(directory_path, filename)
            # Analyze the log file and accumulate the results
            matches, p1_wins, p1_draws, p1_losses, p1_rewards, _ = analyze_log_file(log_file_path)
            all_matches.extend(matches)
            all_p1_wins.extend(p1_wins)
            all_p1_draws.extend(p1_draws)
            all_p1_losses.extend(p1_losses)
            all_p1_rewards.extend(p1_rewards)

    # Calculate statistics for all files
    total_games = len(all_p1_wins) + len(all_p1_draws) + len(all_p1_losses)
    win_rate = len(all_p1_wins) / total_games
    draw_rate = len(all_p1_draws) / total_games
    loss_rate = len(all_p1_losses) / total_games
    average_win_margin = np.mean([gain for gain in all_p1_rewards if gain > 0]) if all_p1_wins else 0
    average_loss_margin = np.mean([abs(gain) for gain in all_p1_rewards if gain < 0]) if all_p1_losses else 0
    std_deviation = np.std(all_p1_rewards)

    stats = {
        'total_games': total_games,
        'win_rate': win_rate,
        'draw_rate': draw_rate,
        'loss_rate': loss_rate,
        'average_win_margin': average_win_margin,
        'average_loss_margin': average_loss_margin,
        'std_deviation': std_deviation,
        'expected_value': win_rate * average_win_margin - loss_rate * average_loss_margin
    }

    return all_matches, all_p1_wins, all_p1_draws, all_p1_losses, all_p1_rewards, stats

def action_counts(hand_list):
    fold_count = 0
    call_or_check_count = 0

    for hand in hand_list:
        parts = hand.split(':')
        actions = parts[2]  # Assuming that the action sequence is the third part of the log entry

        if actions.endswith('f'):
            fold_count += 1
        elif actions.endswith('c'):
            call_or_check_count += 1

    return fold_count, call_or_check_count

def action_lists(hand_list):
    fold_hands = []
    call_or_check_hands = []

    for hand in hand_list:
        parts = hand.split(':')
        actions = parts[2]  # Assuming that the action sequence is the third part of the log entry

        # Extrair o ganho do jogador TCC_AI, que pode estar na quinta ou sexta posição da linha,
        # dependendo de quem começou jogando a partida
        if int(parts[1]) % 2 == 0:
            if int(parts[4].split('|')[1]) != -100:
                continue
        else:
            if int(parts[4].split('|')[0]) != -100:
                continue

        if actions.endswith('f'):
            fold_hands.append(hand)
        elif actions.endswith('c'):
            call_or_check_hands.append(hand)

    return fold_hands, call_or_check_hands

def autolabel(rects, ax, percentages):
    """Attach a text label above each bar in rects, displaying its height."""
    for rect, percentage in zip(rects, percentages):
        height = rect.get_height()
        ax.annotate('{:.0f}%'.format(percentage),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

def plot_action_analysis(wins, losses):
    win_fold_count, win_call_or_check_count = action_counts(wins)
    loss_fold_count, loss_call_or_check_count = action_counts(losses)

    total_wins = len(wins)
    total_losses = len(losses)

    win_fold_percentage = (win_fold_count / total_wins) * 100 if total_wins > 0 else 0
    loss_fold_percentage = (loss_fold_count / total_losses) * 100 if total_losses > 0 else 0

    # Adjust the percentages to sum up to 100
    win_fold_percentage = round(win_fold_percentage, 2)
    loss_fold_percentage = round(loss_fold_percentage, 2)

    win_call_or_check_percentage = round(100 - win_fold_percentage, 2)
    loss_call_or_check_percentage = round(100 - loss_fold_percentage, 2)

    categories = ['Wins', 'Losses']
    folds = [win_fold_percentage, loss_fold_percentage]
    calls_checks = [win_call_or_check_percentage, loss_call_or_check_percentage]

    x = np.arange(len(categories))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width/2, folds, width, label='Folds')
    rects2 = ax.bar(x + width/2, calls_checks, width, label='Calls/Checks')

    # Set the y-axis to go up to 100
    ax.set_ylim(0, 100)

    ax.set_ylabel('Percentage')
    ax.set_title('Action percentages for Wins and Losses')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()

    autolabel(rects1, ax, folds)
    autolabel(rects2, ax, calls_checks)

    fig.tight_layout()
    plt.show()

def main(directory_path, directory_path_2, directory_path_3):
    all_matches_log1, wins, draws, losses, rewards, stats = analyze_directory(directory_path)
    all_matches_log2, wins2, draws2, losses2, rewards2, stats2 = analyze_directory(directory_path_2)
    all_matches_log3, wins3, draws3, losses3, rewards3, stats3 = analyze_directory(directory_path_3)


    print("\nStatistics for TCC_AI on seat 1 and DeepStack on seat 2:")
    for stat, value in stats.items():
        print(f"{stat.replace('_', ' ').title()}: {value}")

    print("\nStatistics for DeepStack on seat 1 and TCC_AI on seat 2:")
    for stat, value in stats2.items():
        print(f"{stat.replace('_', ' ').title()}: {value}")

    plot_statistics(rewards, rewards2, rewards3)

    all_matches = wins + draws + losses
    p1_should_win, p1_should_draw, p1_should_lose = get_hand_quality_proportion(all_matches)

    print("\nlen(all_matches) old: ", len(all_matches))
    print("p1_should_win: ", len(p1_should_win)/len(all_matches))
    print("p1_should_draw: ", len(p1_should_draw)/len(all_matches))
    print("p1_should_lose: ", len(p1_should_lose)/len(all_matches))

    # p1_should_win3, p1_should_draw3, p1_should_lose3 = get_hand_quality_proportion(all_matches_log1)

    # print("\nlen(all_matches) log1: ", len(all_matches_log1))
    # print("p1_should_win: ", len(p1_should_win3)/len(all_matches_log1))
    # print("p1_should_draw: ", len(p1_should_draw3)/len(all_matches_log1))
    # print("p1_should_lose: ", len(p1_should_lose3)/len(all_matches_log1))

    all_matches2 = wins2 + draws2 + losses2
    p1_should_win2, p1_should_draw2, p1_should_lose2 = get_hand_quality_proportion(all_matches2)

    print("\nlen(all_matches) old: ", len(all_matches2))
    print("p1_should_win: ", len(p1_should_win2)/len(all_matches2))
    print("p1_should_draw: ", len(p1_should_draw2)/len(all_matches2))
    print("p1_should_lose: ", len(p1_should_lose2)/len(all_matches2))

    # p1_should_win4, p1_should_draw4, p1_should_lose4 = get_hand_quality_proportion(all_matches_log2)

    # print("\nlen(all_matches) log2: ", len(all_matches_log2))
    # print("p1_should_win: ", len(p1_should_win4)/len(all_matches_log2))
    # print("p1_should_draw: ", len(p1_should_draw4)/len(all_matches_log2))
    # print("p1_should_lose: ", len(p1_should_lose4)/len(all_matches_log2))

    #plot_statistics(rewards, stats)
    #plot_action_analysis(wins, losses)
    #plot_gaussian(rewards)
    #plot_histogram(rewards)
    # wins_folds_list, wins_checkcall_lists = action_lists(wins)
    # losses_folds_list, losses_checkcall_lists = action_lists(losses)
    # print("losses_folds_list:")
    # for hand in losses_folds_list:
    #     print(hand, end=' ')


if __name__ == "__main__":
    # Check if the directory path is provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python script.py <directory_path>")
        sys.exit(1)

    log_folder_path = f'{directory_path}/../logs/matches/' + sys.argv[1]  # Get the directory path from the command-line argument
    log_folder_path2 = f'{directory_path}/../logs/matches/' + sys.argv[2]  # Get the directory path from the command-line argument
    log_folder_path3 = f'{directory_path}/../logs/matches/' + sys.argv[3]  # Get the directory path from the command-line argument

    if not os.path.isdir(log_folder_path):
        print(f"The provided directory does not exist: {sys.argv[1]}")
        sys.exit(1)

    if not os.path.isdir(log_folder_path2):
        print(f"The provided directory does not exist: {sys.argv[2]}")
        sys.exit(1)
    

    if len(sys.argv) == 5:
        is_inverted_seat = sys.argv[3]

    main(log_folder_path, log_folder_path2, log_folder_path3)