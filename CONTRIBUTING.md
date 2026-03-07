# Contributing

## Setup

Run the full stack:

```bash
make start
```

or:

```bash
docker compose up --build
```

## Before Opening a PR

Run:

```bash
python3 -m pip install -r game_engine/requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
cd frontend && npm ci && npm run lint && npm run test && npm run build
```

Optional reproducibility mode for backend tests:

```bash
export POKER_ML_RANDOM_SEED=42
export POKER_ML_CHIP_MODE=persistent_match
```

## Pull Request Guidelines

- Keep changes scoped and explain behavior impact clearly.
- Update `README.md` when run commands or architecture change.
- Include test/build evidence in PR description.
- Do not commit secrets, large generated outputs, or local env files.
- If you need the archived research logs or blueprint bundles, publish them with `./scripts/publish_research_artifacts.sh <tag> <source-ref>` and document the tag used by `scripts/fetch_research_artifacts.sh`.
