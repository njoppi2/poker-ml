"""Run with python -m game_engine.training.benchmark --help."""
import argparse
import hashlib
import json
import math
import pickle
import platform
import subprocess
import sys
import time
from pathlib import Path

from .evaluate import evaluate, validate_policy
from .game import LeducGame
from .solver import ExternalSampling, LegacySampling, restore

SCHEMA = "modified-leduc-v1"
SOLVERS = {"external": ExternalSampling, "legacy": LegacySampling}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def save_checkpoint(path, solver, seed, train_seconds):
    data = {"schema": SCHEMA, "seed": seed, "train_seconds": train_seconds, "state": solver.state_dict()}
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL))
    temporary.replace(path)


def load_checkpoint(path):
    # Only load trusted local checkpoints: pickle is an executable format.
    data = pickle.loads(path.read_bytes())
    if data.get("schema") != SCHEMA:
        raise ValueError("incompatible checkpoint schema")
    return data


def load_blueprint(game, path, missing="call"):
    model = pickle.loads(path.read_bytes())
    extra = set(model) - set(game.info_by_key)
    if extra:
        raise ValueError(f"blueprint contains {len(extra)} states outside this game; check --chips")
    policy, missing_count = [], 0
    for info in game.infosets:
        entry = model.get(info.key)
        if entry is None:
            missing_count += 1
            if missing == "uniform":
                row = [1.0 / len(info.actions)] * len(info.actions)
            else:
                # Historical runtime returns 'c' when a lookup misses: call a
                # bet, or check if no bet is outstanding. Forced passes have
                # only one action. This is a legal-policy completion, not a
                # claim that the websocket engine implements every edge case.
                history = info.key.split(":|")[0]
                action = int(bool(history) and history[-1].isdigit() and len(info.actions) > 1)
                row = [float(i == action) for i in range(len(info.actions))]
        else:
            actions, row = entry
            if tuple(actions) != info.actions:
                raise ValueError(f"blueprint action mismatch at {info.key}")
        policy.append(list(row))
    validate_policy(game, policy)
    return policy, missing_count


def run(game, solver, seed, output, iterations, eval_every, target, max_seconds, previous_seconds=0.0):
    output.mkdir()
    rows = []
    train_seconds = previous_seconds
    run_start_seconds = train_seconds
    initial_iteration = solver.iterations
    reached = False
    stop_reason = "iterations"
    while True:
        eval_start = time.perf_counter()
        policy = solver.average_policy()
        metrics = evaluate(game, policy)
        eval_seconds = time.perf_counter() - eval_start
        row = {"algorithm": solver.name, "seed": seed, "iteration": solver.iterations,
               "train_seconds": train_seconds, "evaluation_seconds": eval_seconds,
               "node_visits": solver.node_visits, "visited_infosets": len(solver.visited),
               "total_infosets": len(game.infosets), **metrics}
        rows.append(row)
        with (output / "metrics.jsonl").open("a") as handle:
            handle.write(json.dumps(row, allow_nan=False) + "\n")
        save_checkpoint(output / "checkpoint.pkl", solver, seed, train_seconds)
        print(f"{solver.name} seed={seed} iteration={solver.iterations} "
              f"train={train_seconds:.3f}s exploitability={metrics['exploitability']:.6f} BB/hand", flush=True)
        reached = target is not None and metrics["exploitability"] <= target
        if reached:
            stop_reason = "target"
            break
        if solver.iterations >= iterations:
            break
        if max_seconds is not None and train_seconds - run_start_seconds >= max_seconds:
            stop_reason = "time_budget"
            break
        next_eval = min(iterations, (solver.iterations // eval_every + 1) * eval_every)
        block_start = time.perf_counter()
        while solver.iterations < next_eval:
            solver.iteration()
            if (max_seconds is not None and solver.iterations % 100 == 0
                    and train_seconds - run_start_seconds + time.perf_counter() - block_start >= max_seconds):
                break
        train_seconds += time.perf_counter() - block_start
    blueprint = {info.key: (list(info.actions), probabilities) for info, probabilities in zip(game.infosets, policy)}
    (output / "policy.pkl").write_bytes(pickle.dumps(blueprint, protocol=pickle.HIGHEST_PROTOCOL))
    result = {"algorithm": solver.name, "seed": seed, "initial_iteration": initial_iteration,
              "target": target, "target_reached": reached, "stop_reason": stop_reason,
              "final": rows[-1]}
    write_json(output / "summary.json", result)
    return result


def parser():
    p = argparse.ArgumentParser(description="Exact convergence benchmark for the original modified Leduc game.")
    p.add_argument("--chips", type=int, help="starting stack in ante/BB units, 2..12 (default 12)")
    p.add_argument("--algorithms", nargs="+", choices=SOLVERS, help="default external legacy")
    p.add_argument("--seeds", nargs="+", type=int, help="default 42")
    p.add_argument("--iterations", type=int, default=20000, help="total iteration ceiling, including resumed iterations")
    p.add_argument("--eval-every", type=int, default=1000)
    p.add_argument("--target", type=float, help="stop at first checkpoint at/below this exploitability (BB/hand)")
    p.add_argument("--max-seconds", type=float, help="training-time budget per run, checked every 100 iterations")
    p.add_argument("--output", type=Path, required=True, help="new directory; existing results are never overwritten")
    p.add_argument("--resume", type=Path, help="trusted checkpoint.pkl; retains algorithm, seed and RNG state")
    p.add_argument("--evaluate-blueprint", type=Path, help="evaluate a trusted legacy-format policy pickle, without training")
    p.add_argument("--missing", choices=["call", "uniform"], default="call", help="completion for absent blueprint states")
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.iterations < 0 or args.eval_every <= 0:
        p.error("iterations must be nonnegative and eval-every must be positive")
    if args.target is not None and (not math.isfinite(args.target) or args.target < 0):
        p.error("target must be finite and nonnegative")
    if args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0):
        p.error("max-seconds must be finite and positive")
    if args.resume and (args.algorithms or args.seeds or args.evaluate_blueprint):
        p.error("resume cannot be combined with algorithms, seeds, or evaluate-blueprint")
    if args.evaluate_blueprint and (args.algorithms or args.seeds):
        p.error("evaluate-blueprint cannot be combined with algorithms or seeds")
    if args.output.exists():
        p.error("output already exists; choose a new directory")
    checkpoint = load_checkpoint(args.resume) if args.resume else None
    chips = args.chips if args.chips is not None else (checkpoint["state"]["chips"] if checkpoint else 12)
    if not 2 <= chips <= 12:
        p.error("chips must be from 2 to 12")
    if checkpoint and (checkpoint["state"]["chips"] != chips or checkpoint["state"]["iterations"] > args.iterations):
        p.error("resume requires matching chips and iterations >= the saved iteration")
    setup_start = time.perf_counter()
    game = LeducGame(chips)
    setup_seconds = time.perf_counter() - setup_start
    args.output.mkdir(parents=True)
    source_root = Path(__file__).resolve().parents[1]
    source_files = sorted((source_root / "training").glob("*.py")) + [
        source_root / "ia" / "algorithms" / name
        for name in ("mod_leduc.py", "classes.py", "functions.py")
    ]
    source_hashes = {str(path.relative_to(source_root)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in source_files}
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True))
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    metadata = {"schema": SCHEMA, "python": sys.version, "platform": platform.platform(),
                "git_revision": revision, "git_dirty": dirty, "chips": chips, "unit": "BB/hand (1 BB = 1 ante unit)",
                "public_nodes": len(game.nodes), "infosets": len(game.infosets), "rank_deals": len(game.deals),
                "setup_seconds": setup_seconds, "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "source_sha256": source_hashes,
                "iteration_definitions": {"external": "two traversals, one per updating player; independent chance deals",
                                          "legacy": "one historical mixed traversal and one shuffled deal"},
                "timing": "training excludes compilation, exact evaluation, policy export and checkpoint IO"}
    write_json(args.output / "metadata.json", metadata)
    if args.evaluate_blueprint:
        rows, missing = load_blueprint(game, args.evaluate_blueprint, args.missing)
        start = time.perf_counter()
        result = {"blueprint": str(args.evaluate_blueprint.resolve()), "missing_infosets": missing,
                  "missing_completion": args.missing, **evaluate(game, rows)}
        result["evaluation_seconds"] = time.perf_counter() - start
        write_json(args.output / "summary.json", result)
        print(json.dumps(result, indent=2))
        return
    results = []
    if checkpoint:
        runs = [(restore(game, checkpoint["state"]), checkpoint["seed"], checkpoint["train_seconds"])]
    else:
        algorithms = list(dict.fromkeys(args.algorithms or ["external", "legacy"]))
        seeds = list(dict.fromkeys(args.seeds or [42]))
        runs = ((SOLVERS[name](game, seed), seed, 0.0) for name in algorithms for seed in seeds)
    for solver, seed, previous_seconds in runs:
        results.append(run(game, solver, seed, args.output / f"{solver.name}-{seed}", args.iterations,
                           args.eval_every, args.target, args.max_seconds, previous_seconds))
    write_json(args.output / "summary.json", results)


if __name__ == "__main__":
    main()
