import sys
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def plot_statistics(rewards, stats):
    # Convert rewards to a pandas Series for cumulative sum
    rewards_series = pd.Series(rewards).cumsum()

    # Plot the bankroll over time
    plt.figure(figsize=(12, 6))
    rewards_series.plot(title='Bankroll Over Time')
    plt.xlabel('Game Number')
    plt.ylabel('Bankroll')
    plt.grid(True)
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

    # Plot win/loss streaks
    labels = ['Longest Win Streak', 'Longest Loss Streak', 'Max Streak']
    values = [stats['longest_win_streak'], stats['longest_loss_streak'], stats['max_streak']]

    plt.figure(figsize=(8, 5))
    plt.bar(labels, values, color=['blue', 'red', 'purple'])
    plt.title('Win and Loss Streaks')
    plt.ylabel('Number of Games')
    for i, v in enumerate(values):
        plt.text(i, v + 0.25, str(v), color='black', ha='center')
    plt.tight_layout()
    plt.show()

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
    
    # Calculate win/loss streaks
    current_streak = max_streak = win_streak = loss_streak = 0
    for gain in rewards:
        if gain > 0:
            if current_streak >= 0:
                current_streak += 1
            else:
                current_streak = 1
            win_streak = max(win_streak, current_streak)
        elif gain < 0:
            if current_streak <= 0:
                current_streak -= 1
            else:
                current_streak = -1
            loss_streak = max(loss_streak, -current_streak)
        else:
            current_streak = 0
        max_streak = max(max_streak, abs(current_streak))

    stats = {
        'total_games': total_games,
        'win_rate': win_rate,
        'draw_rate': draw_rate,
        'loss_rate': loss_rate,
        'average_win_margin': average_win_margin,
        'average_loss_margin': average_loss_margin,
        'std_deviation': std_deviation,
        'longest_win_streak': win_streak,
        'longest_loss_streak': loss_streak,
        'max_streak': max_streak
    }

    return tcc_ai_wins, tcc_ai_draws, tcc_ai_losses, rewards, stats

def main(log_file_path):
    wins, draws, losses, rewards, stats = analyze_log_file(log_file_path)
    print("\nStatistics:")
    for stat, value in stats.items():
        print(f"{stat.replace('_', ' ').title()}: {value}")
    plot_statistics(rewards, stats)



if __name__ == "__main__":
    log_file_name = "important_logs/4kk_noParamenters_10kgames.log"
    main(log_file_name)
