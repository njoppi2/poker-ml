# Poker ML

[![CI](https://img.shields.io/github/actions/workflow/status/njoppi2/poker-ml/ci.yml?branch=main&label=CI)](https://github.com/njoppi2/poker-ml/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/njoppi2/poker-ml)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/njoppi2/poker-ml)](https://github.com/njoppi2/poker-ml/commits/main)

Poker AI project from our undergraduate final project (TCC), combining strategy experimentation, a Python websocket game engine, and a React frontend for interactive play.

## Snapshot

![Poker table UI asset](frontend/public/assets/table.svg)

## Problem

Provide a compact research and experimentation environment to simulate poker rounds, evaluate agent behavior, and expose game state through a real-time UI.

## Tech Stack

- Python (game engine and AI routines)
- React frontend (Vite)
- WebSockets
- Docker / Docker Compose

## Repository Layout

- `game_engine/`: game logic, websocket server, and AI modules
- `frontend/`: web interface
- `tests/`: test utilities and API interaction script
- `TCC_Monografia.pdf`: monograph

## Quickstart

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

## Run Services Manually

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
npm run dev
```

## Validation and CI

Local checks:

```bash
PYTHONPATH=. python -m unittest discover -s tests -p "test_*.py"
cd frontend && npm ci && npm run build
```

CI (`.github/workflows/ci.yml`) validates:

- Python syntax compilation in `game_engine`
- Backend unit tests in `tests/`
- Frontend production build

## Results

- Supports Leduc and Texas Hold'em modes.
- Runs full agent-vs-human round flow over websocket events.
- Includes baseline test suite and frontend build gate.

## Limitations

- Large training artifacts are still in-repo.
- Training runs are not fully reproducible from one CLI entrypoint.
- Websocket end-to-end test coverage is still limited.

## Roadmap

- Move large artifacts to GitHub Releases/LFS.
- Add deterministic websocket integration tests.
- Add experiment tracking metadata for training runs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
