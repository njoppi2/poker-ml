# Poker ML

[![CI](https://img.shields.io/github/actions/workflow/status/njoppi2/poker-ml/ci.yml?branch=main&label=CI)](https://github.com/njoppi2/poker-ml/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/njoppi2/poker-ml)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/njoppi2/poker-ml)](https://github.com/njoppi2/poker-ml/commits/main)

Poker AI project from our undergraduate final project (TCC), combining strategy experimentation, a Python websocket game engine, and a React frontend for interactive play.

## Problem

Provide a compact research and experimentation environment to simulate poker rounds, evaluate agent behavior, and expose game state through a real-time UI.

## Tech Stack

- Python (game engine and AI routines)
- React frontend (Vite)
- WebSockets
- Docker / Docker Compose

## Repository Layout

- `game_engine/`: packaged backend, websocket server, and runtime AI policy
- `frontend/`: web interface
- `tests/`: backend unit tests
- `artifacts/`: research artifact manifest
- `scripts/`: helper scripts such as research artifact download
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
python3 -m pip install -r game_engine/requirements.txt
python3 -m game_engine.main
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Local development falls back to `ws://localhost:3002`.
`VITE_WS_URL` remains available as an optional manual override if you want the frontend to target a non-default websocket endpoint.

## Validation and CI

Local checks:

```bash
python3 -m pip install -r game_engine/requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
cd frontend && npm ci && npm run lint && npm run test && npm run build
```

CI (`.github/workflows/ci.yml`) validates:

- Python syntax compilation in `game_engine`
- Backend unit tests in `tests/`
- Backend websocket integration coverage
- Frontend lint
- Frontend unit tests
- Frontend production build
- Docker image builds through `docker compose build`

## Deterministic Mode (Backend)

For reproducible backend behavior during tests/debugging, set:

```bash
export POKER_ML_RANDOM_SEED=42
export POKER_ML_CHIP_MODE=persistent_match
export POKER_ML_MODEL_PATH="$(pwd)/game_engine/models/runtime/IOu-mccfr-6cards-11maxbet-EPcfr0_0-mRW0_0-iter100000000.pkl"
```

Other useful backend env vars:

- `POKER_ML_WS_HOST`
- `POKER_ML_WS_PORT`
- `POKER_ML_MAX_ROUNDS`

## WebSocket Smoke Coverage

- `tests/test_websocket_smoke.py` validates legacy and JSON websocket start messages.
- `tests/test_websocket_integration.py` exercises a real websocket session through the server.
- `tests/test_random_control.py` validates deterministic seed handling.
- `tests/test_game_modes.py` validates persistent vs reset-each-round chip behavior.

## Results

- Supports Leduc and Texas Hold'em modes with explicit chip modes.
- Runs full agent-vs-human round flow over websocket events.
- Includes backend unit coverage plus frontend lint/test/build gates.
- Operates as a local-first stack through Docker Compose or direct local processes.

## Research Artifacts

The runtime model now lives under `game_engine/models/runtime/`. Research-only logs and extra blueprint snapshots were removed from the active source tree and should be published as GitHub Release assets described in `artifacts/research-manifest.json`.

Publish the release assets from a source ref that still contains the archived files:

```bash
./scripts/publish_research_artifacts.sh research-artifacts HEAD
```

Fetch them after publishing a release:

```bash
./scripts/fetch_research_artifacts.sh
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
