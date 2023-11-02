import sys

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

    # Retornar os resultados
    print(rewards)
    return tcc_ai_wins, tcc_ai_draws, tcc_ai_losses

def main(log_file_path):
    wins, draws, losses = analyze_log_file(log_file_path)
    # Imprimir os resultados
    print("\nPartidas ganhas pelo TCC_AI:", wins[0])
    print("\nPartidas empatadas pelo TCC_AI:", draws[0])
    print("\nPartidas perdidas pelo TCC_AI:", losses[0])

if __name__ == "__main__":
    log_file_name = "important_logs/4kk_noParamenters_10kgames.log"
    main(log_file_name)
