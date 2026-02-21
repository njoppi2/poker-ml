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
PYTHONPATH=. python -m unittest discover -s tests -p "test_*.py"
cd frontend && npm ci && npm run build
```

Optional reproducibility mode for backend tests:

```bash
export POKER_ML_RANDOM_SEED=42
```

## Pull Request Guidelines

- Keep changes scoped and explain behavior impact clearly.
- Update `README.md` when run commands or architecture change.
- Include test/build evidence in PR description.
- Do not commit secrets, large generated outputs, or local env files.
