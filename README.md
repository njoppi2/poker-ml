# Poker ML

Poker AI project developed during our undergraduate final project (TCC), with:

- training and analysis artifacts for poker strategies,
- a Python websocket game engine,
- and a React frontend to play against the AI.

The monograph is available in `TCC_Monografia.pdf`.

## Tech Stack

- Python (game engine + AI routines)
- React frontend
- WebSockets
- Docker / Docker Compose

## Repository Layout

- `game_engine/`: game logic, websocket server, and AI-related modules
- `frontend/`: web interface
- `tests/`: API interaction script and test utilities
- `TCC_Monografia.pdf`: project write-up

## Quickstart (Docker)

From repository root:

```bash
make start
```

or:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend websocket: `ws://localhost:3002`

Stop:

```bash
make stop
```

or:

```bash
docker compose down
```

## Running Services Manually

Backend:

```bash
cd game_engine
pip install -r requirements.txt
python main.py
```

Frontend:

```bash
cd frontend
npm install
npm start
```

## Testing

Utility/unit tests:

```bash
PYTHONPATH=. python -m unittest discover -s tests -p "test_*.py"
```

API interaction script:

```bash
python tests/sample_api.py --help
```

## What This Project Demonstrates

- multi-street poker simulation support (including Leduc and Texas Hold'em modes),
- agent-vs-human game loop over websocket events,
- AI training/blueprint experimentation for decision-making.

## Limitations / Next Improvements

- Move large training artifacts to GitHub Releases or Git LFS.
- Add reproducible training entrypoints and experiment tracking metadata.
- Add automated tests for websocket game flow.
