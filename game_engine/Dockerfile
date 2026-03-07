FROM python:3.10.12

WORKDIR /app

COPY game_engine/requirements.txt /app/game_engine/requirements.txt
RUN pip install -r /app/game_engine/requirements.txt

COPY game_engine /app/game_engine

EXPOSE 3002

CMD ["python", "-m", "game_engine.main"]
