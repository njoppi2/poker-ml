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

def plot_statistics(rewards, stats):
    # Convert rewards to a pandas Series for cumulative sum
    rewards_series = pd.Series(rewards).cumsum()

    # Calcular a média acumulada
    media_acumulada = rewards_series / np.arange(1, len(rewards) + 1)

    # Calcular o desvio padrão acumulado
    desvios = [rewards_series.iloc[:i+1].std(ddof=1) if i > 0 else 0 for i in range(len(rewards))]

    # Plot the rewards over time
    plt.figure(figsize=(12, 6))

    plt.plot(rewards, label='Ganhos', alpha=0.5)
    plt.plot(media_acumulada, label='Média Acumulada', color='red')

    # Plotar o desvio padrão acumulado
    plt.fill_between(range(len(rewards)), media_acumulada - desvios, media_acumulada + desvios, color='gray', alpha=0.2, label='Desvio Padrão Acumulado')

    # Adicionar título e legenda
    plt.title('Ganhos com Média e Desvio Padrão Acumulados')
    plt.xlabel('Número de Amostras')
    plt.ylabel('Valor')
    plt.legend()

    # Mostrar o plot
    plt.show()

    # Plot the win/draw/loss distribution
    labels = 'Wins', 'Draws', 'Losses'
    sizes = [stats['win_rate'], stats['draw_rate'], stats['loss_rate']]
    colors = ['green', 'gold', 'red']
    explode = (0.1, 0, 0)  # explode 1st slice (Wins)

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')
    plt.title('Game Outcome Distribution')
    plt.show()

def is_winning_hand(line):
    CARDS_RANK = {'Q': 0, 'K': 1, 'A': 2, 'Pair': 3}
    parts = line.split(':')
    cards = parts[3].split('/')
    if int(parts[1]) % 2 == 0:
        my_card = cards[0].split('|')[1]
        op_card = cards[0].split('|')[0]
        my_card = ''.join(filter(str.isupper, my_card))
        op_card = ''.join(filter(str.isupper, op_card))

    else:
        my_card = cards[0].split('|')[0]
        op_card = cards[0].split('|')[1]
        my_card = ''.join(filter(str.isupper, my_card))
        op_card = ''.join(filter(str.isupper, op_card))

    if len(cards) > 1:
        cards[1] = ''.join(filter(str.isupper, cards[1]))

    if (len(cards) > 1 and my_card == cards[1]):
        my_rank = 3
    else:
        my_rank = CARDS_RANK[my_card]

    if (len(cards) > 1 and op_card == cards[1]):
        op_rank = 3
    else:
        op_rank = CARDS_RANK[op_card]

    if (my_rank > op_rank):
        return True
    else:
        return False

def is_losing_hand(line):
    cards_rank = {'Q': 0, 'K': 1, 'A': 2, 'Pair': 3}
    parts = line.split(':')
    cards = parts[3].split('/')
    if int(parts[1]) % 2 == 0:
        my_card = cards[0].split('|')[1]
        op_card = cards[0].split('|')[0]
        my_card = ''.join(filter(str.isupper, my_card))
        op_card = ''.join(filter(str.isupper, op_card))
    else:
        my_card = cards[0].split('|')[0]
        op_card = cards[0].split('|')[1]
        my_card = ''.join(filter(str.isupper, my_card))
        op_card = ''.join(filter(str.isupper, op_card))
    
    if len(cards) > 1:
        cards[1] = ''.join(filter(str.isupper, cards[1]))

    if (len(cards) > 1 and my_card == cards[1]):
        my_rank = 3
    else:
        my_rank = cards_rank[my_card]

    if (len(cards) > 1 and op_card == cards[1]):
        op_rank = 3
    else:
        op_rank = cards_rank[op_card]

    if (my_rank < op_rank):
        return True
    else:
        return False        

def print_matchlist_analysis(matchlist):
    bad_hands = [match for match in matchlist if is_losing_hand(match)]
    good_hands = [match for match in matchlist if is_winning_hand(match)]
    print("Should have lost: ", len(bad_hands)/len(matchlist))
    print("Should have won: ", len(good_hands)/len(matchlist))
    print("Should have draw: ", 1 - (len(bad_hands)/len(matchlist) + len(good_hands)/len(matchlist)))

def get_hand_quality_proportion(matchlist):
    CARDS_RANK = {'Q': 0, 'K': 1, 'A': 2, 'Pair': 3}
    p1_should_win = []
    p1_should_draw = []
    p1_should_lose = []

    for line in matchlist:
        parts = line.split(':')
        cards = parts[3].split('/')

        p1_card = ''.join(filter(str.isupper, cards[0].split('|')[0]))
        p2_card = ''.join(filter(str.isupper, cards[0].split('|')[1]))

        p1_rank = CARDS_RANK[p1_card]
        p2_rank = CARDS_RANK[p2_card]

        # Check for the common card and adjust the rank if there's a pair
        if len(cards) > 1 and cards[1].strip():
            common_card = ''.join(filter(str.isupper, cards[1]))
            if p1_card == common_card:
                p1_rank = CARDS_RANK['Pair']
            if p2_card == common_card:
                p2_rank = CARDS_RANK['Pair']

        # Compare the ranks to determine win, draw, or loss
        if p1_rank > p2_rank:
            p1_should_win.append(line)
        elif p1_rank == p2_rank:
            p1_should_draw.append(line)
        else:
            p1_should_lose.append(line)

    return p1_should_win, p1_should_draw, p1_should_lose

def analyze_log_file(log_file_path):
    # Vetores para armazenar as partidas ganhas, empatadas e perdidas pelo TCC_AI
    tcc_ai_wins = []
    tcc_ai_draws = []
    tcc_ai_losses = []
    rewards = []


    # Abrir o arquivo e ler linha por linha
    with open(log_file_path, 'r') as file:
        for line in file:
            # Verificar se a linha começa com "STATE:"
            if line.startswith("STATE:"):
                # Separar os componentes da linha
                parts = line.split(':')

                # Extrair o ganho do jogador TCC_AI, que pode estar na quinta ou sexta posição da linha,
                # dependendo de quem começou jogando a partida
                if int(parts[1]) % 2 == 0:
                    tcc_ai_gain = int(parts[4].split('|')[1])

                else:
                    tcc_ai_gain = int(parts[4].split('|')[0])

                # Adicionar o ganho do jogador TCC_AI ao vetor de recompensas
                if is_inverted_seat:
                    tcc_ai_gain = -int(tcc_ai_gain)
                else:
                    tcc_ai_gain = int(tcc_ai_gain)
                rewards.append(int(tcc_ai_gain))

                # Classificar a partida como ganha, empatada ou perdida
                if tcc_ai_gain > 0:
                    tcc_ai_wins.append(line)
                elif tcc_ai_gain == 0:
                    tcc_ai_draws.append(line)
                else:
                    tcc_ai_losses.append(line)

    # Calculate statistics
    total_games = len(tcc_ai_wins) + len(tcc_ai_draws) + len(tcc_ai_losses)
    win_rate = len(tcc_ai_wins) / total_games
    draw_rate = len(tcc_ai_draws) / total_games
    loss_rate = len(tcc_ai_losses) / total_games
    average_win_margin = np.mean([gain for gain in rewards if gain > 0]) if tcc_ai_wins else 0
    average_loss_margin = np.mean([abs(gain) for gain in rewards if gain < 0]) if tcc_ai_losses else 0
    std_deviation = np.std(rewards)

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

    return tcc_ai_wins, tcc_ai_draws, tcc_ai_losses, rewards, stats

def analyze_directory(directory_path):
    # Lists to store the results from all files
    all_tcc_ai_wins = []
    all_tcc_ai_draws = []
    all_tcc_ai_losses = []
    all_rewards = []

    # Loop through each file in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith('.log'):  # Check if the file is a log file
            log_file_path = os.path.join(directory_path, filename)
            # Analyze the log file and accumulate the results
            tcc_ai_wins, tcc_ai_draws, tcc_ai_losses, rewards, _ = analyze_log_file(log_file_path)
            all_tcc_ai_wins.extend(tcc_ai_wins)
            all_tcc_ai_draws.extend(tcc_ai_draws)
            all_tcc_ai_losses.extend(tcc_ai_losses)
            all_rewards.extend(rewards)

    # Calculate statistics for all files
    total_games = len(all_tcc_ai_wins) + len(all_tcc_ai_draws) + len(all_tcc_ai_losses)
    win_rate = len(all_tcc_ai_wins) / total_games
    draw_rate = len(all_tcc_ai_draws) / total_games
    loss_rate = len(all_tcc_ai_losses) / total_games
    average_win_margin = np.mean([gain for gain in all_rewards if gain > 0]) if all_tcc_ai_wins else 0
    average_loss_margin = np.mean([abs(gain) for gain in all_rewards if gain < 0]) if all_tcc_ai_losses else 0
    std_deviation = np.std(all_rewards)

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

    return all_tcc_ai_wins, all_tcc_ai_draws, all_tcc_ai_losses, all_rewards, stats

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

def plot_statistics_overview(stats):
    # Plotting Total Games, Win Rate, Draw Rate, Loss Rate, Average Win Margin, Average Loss Margin, Std Deviation
    categories = ['Win Rate', 'Draw Rate', 'Loss Rate', 'Avg Win Margin', 'Avg Loss Margin', 'Std Deviation']
    values = [stats['win_rate'] * 100, stats['draw_rate'] * 100, stats['loss_rate'] * 100,
              stats['average_win_margin'], stats['average_loss_margin'], stats['std_deviation']]

    plt.figure(figsize=(10, 5))
    bars = plt.bar(categories, values, color='skyblue')

    plt.title('AI Performance Statistics')
    plt.ylabel('Value')
    plt.xticks(rotation=45, ha="right")

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, round(yval, 2), va='bottom')  # Round to 2 decimals

    plt.tight_layout()
    plt.show()

def main(directory_path):
    wins, draws, losses, rewards, stats = analyze_directory(directory_path)
    print("\nStatistics:")
    for stat, value in stats.items():
        print(f"{stat.replace('_', ' ').title()}: {value}")
    plot_statistics(rewards, stats)
    plot_action_analysis(wins, losses)
    plot_statistics_overview(stats)
    plot_gaussian(rewards)
    plot_histogram(rewards)
    
    all_matches = wins + draws + losses
    p1_should_win, p1_should_draw, p1_should_lose = get_hand_quality_proportion(all_matches)

    print("p1_should_win: ", len(p1_should_win)/len(all_matches))
    print("p1_should_draw: ", len(p1_should_draw)/len(all_matches))
    print("p1_should_lose: ", len(p1_should_lose)/len(all_matches))

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
    if not os.path.isdir(log_folder_path):
        print(f"The provided directory does not exist: {sys.argv[1]}")
        sys.exit(1)

    if len(sys.argv) == 3:
        is_inverted_seat = sys.argv[2]
    main(log_folder_path)