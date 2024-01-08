# Poker-ml
Este repositório apresenta tanto o nosso algoritmo de treinamento da IA, contido na pasta "game_engine/ia", tanto a nossa aplicação web que permite jogar o HUNL Leduc Poker contra ela.

<br />
<br />

## Rodando interface WEB:
(Primeiro é necessário ter a Docker Engine instalada)

A partir do root do projeto, execute os seguintes comandos para iniciar a aplicação:
```
make start
```
ou
```
docker compose up
```

Agora abra em algum browser de preferencia a seguinte URL:
```
http://localhost:3000/
```

### Só jogar agora :)

<br />
<br />

## Para parar de rodar a app WEB:
```
make stop
```
ou
```
docker compose down
```
