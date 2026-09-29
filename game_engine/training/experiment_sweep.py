"""Comparable wall-clock experiments; alternatives stay outside the app trainer.

Run with ``python -m game_engine.training.experiment_sweep --help``. Build and
shared game compilation are reported separately. Each run includes solver
initialization, state transfer, training, opponent generation, and evaluation.
Final artifact serialization is excluded. Evaluation checkpoints are observations,
not interpolated claims about the exact time a threshold was first crossed.
"""
import argparse
import gc
import hashlib
import json
import math
import os
import pickle
import platform
import subprocess
import time
from pathlib import Path

from .evaluate import evaluate
from .game import LeducGame


def make_solver(game, method, seed, warm_state=None, warm_policy=None):
    if method == "external":
        from .rust_backend import RustExternalSampling
        return RustExternalSampling(game, seed, state=warm_state)
    if method.startswith("sampled-"):
        from .experimental_sampling import SampledVariant
        if warm_state is not None or warm_policy is not None:
            raise ValueError("sampled experiment warm starts are not supported")
        name = method.removeprefix("sampled-")
        mode, _, rate = name.partition(":")
        return SampledVariant(game, seed, mode=mode, baseline_rate=float(rate) if rate else 0.5)
    if method.startswith("full-"):
        from .experimental_cfr import NativeFullTraversalCFR
        if warm_state is not None or warm_policy is not None:
            raise ValueError("full CFR warm starts are not supported")
        return NativeFullTraversalCFR(game, method.removeprefix("full-"))
    if method == "cfr-br":
        from .experimental_adversarial import NativeCFRBestResponse
        if warm_policy is not None:
            raise ValueError("CFR-BR warm starts are not supported")
        return NativeCFRBestResponse(game)
    if method.startswith("single:"):
        from .experimental_adversarial import NativeHeuristicLeague
        _, step, refresh, self_play = method.split(":")
        return NativeHeuristicLeague(game, step_size=float(step), initial_policy=warm_policy,
                                     refresh_every=int(refresh), max_snapshots=1,
                                     self_play_weight=float(self_play))
    if method.startswith("batch:"):
        from .experimental_adversarial import NativeBatchedSingleExploiter
        _, step, refresh, self_play = method.split(":")
        return NativeBatchedSingleExploiter(game, step_size=float(step), initial_policy=warm_policy,
                                            refresh_every=int(refresh), self_play_weight=float(self_play))
    if method.startswith("counterbatch:"):
        from .experimental_adversarial import NativeCounterExploiterBatch
        parts = method.split(":")
        if len(parts) not in (4, 5):
            raise ValueError("counterbatch syntax: step:responses:self_play[:response_growth]")
        _, step, responses, self_play, *growth = parts
        return NativeCounterExploiterBatch(game, step_size=float(step), initial_policy=warm_policy,
                                           responses=int(responses), self_play_weight=float(self_play),
                                           response_growth=float(growth[0]) if growth else 1.0)
    if method.startswith("colearn:"):
        from .experimental_adversarial import NativeCoTrainingSingleExploiter
        _, step, refresh, self_play, opponent_rate = method.split(":")
        return NativeCoTrainingSingleExploiter(
            game, step_size=float(step), initial_policy=warm_policy, refresh_every=int(refresh),
            self_play_weight=float(self_play), exploiter_step_multiplier=float(opponent_rate))
    if method.startswith(("ed", "league")):
        from .experimental_adversarial import NativeTabularED, NativeHeuristicLeague
        name, _, step = method.partition(":")
        kwargs = {"initial_policy": warm_policy, "step_size": float(step) if step else 0.5}
        if name == "ed":
            return NativeTabularED(game, **kwargs)
        if name == "league":
            return NativeHeuristicLeague(game, **kwargs)
    raise ValueError(f"unknown experiment method: {method}")


def run_one(game, method, seed, seconds, eval_every, output, warm_state=None, warm_policy=None):
    output.mkdir()
    gc.collect()
    started = time.perf_counter()
    solver = make_solver(game, method, seed, warm_state, warm_policy)
    init_seconds = time.perf_counter() - started
    initial_iteration = solver.iterations
    train_seconds = eval_seconds = 0.0
    last_eval_seconds = 0.0
    rows = []
    block = 25_000 if method.startswith(("external", "sampled-")) else 1
    per_iteration = None

    def record():
        nonlocal eval_seconds, last_eval_seconds
        eval_start = time.perf_counter()
        policy = solver.average_policy()
        metrics = evaluate(game, policy)
        last_eval_seconds = time.perf_counter() - eval_start
        eval_seconds += last_eval_seconds
        row = {"method": method, "seed": seed, "iteration": solver.iterations,
               "elapsed_seconds": time.perf_counter() - started,
               "train_seconds": train_seconds, "evaluation_seconds": eval_seconds,
               "initialization_seconds": init_seconds, **metrics}
        rows.append(row)
        with (output / "metrics.jsonl").open("a") as handle:
            handle.write(json.dumps(row, allow_nan=False) + "\n")
        print(json.dumps(row, allow_nan=False), flush=True)
        return policy

    try:
        policy = record()
        next_eval = eval_every
        while True:
            elapsed = time.perf_counter() - started
            remaining = seconds - elapsed - last_eval_seconds
            if remaining <= 0:
                break
            if elapsed + last_eval_seconds >= next_eval:
                policy = record()
                next_eval += eval_every
                continue
            allowance = min(1.5, remaining, next_eval - elapsed - last_eval_seconds)
            if per_iteration is not None:
                block = max(1, min(1_000_000, int(allowance / per_iteration)))
            train_start = time.perf_counter()
            solver.advance(block)
            took = time.perf_counter() - train_start
            train_seconds += took
            per_iteration = took / block
        if rows[-1]["iteration"] != solver.iterations:
            policy = record()
        summary = {"method": method, "seed": seed, "chips": game.chips,
                   "budget_seconds": seconds, "eval_every_seconds": eval_every,
                   "initial_iteration": initial_iteration, "final": rows[-1],
                   "best_observed_exploitability": min(row["exploitability"] for row in rows),
                   "first_observed_threshold_seconds": {
                       str(target): next((row["elapsed_seconds"] for row in rows
                                          if row["exploitability"] <= target), None)
                       for target in (0.1, 0.05, 0.02, 0.01, 0.005, 0.002, 0.001)},
                   "timing": "includes initialization, transfer, training/BRs, and exact evaluations; excludes shared build/game compilation and final artifacts"}
        (output / "policy.pkl").write_bytes(pickle.dumps(policy, protocol=pickle.HIGHEST_PROTOCOL))
        blueprint = {info.key: (list(info.actions), row)
                     for info, row in zip(game.infosets, policy)}
        (output / "blueprint.pkl").write_bytes(pickle.dumps(blueprint, protocol=pickle.HIGHEST_PROTOCOL))
        if hasattr(solver, "state_dict"):
            (output / "state.pkl").write_bytes(pickle.dumps(solver.state_dict(), protocol=pickle.HIGHEST_PROTOCOL))
        (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        return summary
    finally:
        if hasattr(solver, "close"):
            solver.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--methods", nargs="+", default=["external", "sampled-linear", "sampled-vr", "sampled-vr-linear"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--chips", type=int, default=12)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--eval-every", type=float, default=5)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--warm-checkpoint", type=Path)
    parser.add_argument("--warm-blueprint", type=Path)
    parser.add_argument("--warm-policy", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or not math.isfinite(args.seconds) or args.seconds <= 0 or not math.isfinite(args.eval_every) or args.eval_every <= 0:
        parser.error("choose a new output directory and finite positive time budgets")
    if sum(source is not None for source in (args.warm_checkpoint, args.warm_blueprint, args.warm_policy)) > 1:
        parser.error("choose one warm-start source")
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {args.cpu})
    args.output.mkdir(parents=True)
    from .rust_backend import build_kernel
    from .experimental_sampling import build_kernel as build_sampled
    from .experimental_cfr import build_full_cfr_kernel
    build_start = time.perf_counter()
    if "external" in args.methods:
        build_kernel()
    if any(name.startswith("sampled-") for name in args.methods):
        build_sampled()
    if any(name.startswith("full-") for name in args.methods):
        build_full_cfr_kernel()
    if any(name.startswith(("ed", "league", "cfr-br", "single:", "batch:", "counterbatch:", "colearn:")) for name in args.methods):
        from .experimental_adversarial import build_adversarial_kernel
        build_adversarial_kernel()
    build_seconds = time.perf_counter() - build_start
    game_start = time.perf_counter()
    game = LeducGame(args.chips)
    game_seconds = time.perf_counter() - game_start
    state = policy = None
    if args.warm_checkpoint:
        from .benchmark import load_checkpoint
        from .solver import restore
        state = load_checkpoint(args.warm_checkpoint)["state"]
        policy = restore(game, state).average_policy()
    elif args.warm_blueprint:
        from .benchmark import load_blueprint
        policy, missing = load_blueprint(game, args.warm_blueprint)
        if missing:
            parser.error(f"warm blueprint is incomplete: {missing} information sets missing")
    elif args.warm_policy:
        from .evaluate import validate_policy
        policy = pickle.loads(args.warm_policy.read_bytes())
        validate_policy(game, policy)
    root = Path(__file__).parent
    sources = list(root.glob("*.py")) + list(root.glob("*/src/*.rs")) + list(root.glob("*/Cargo.toml"))
    metadata = {"args": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "python": platform.python_version(), "platform": platform.platform(),
                "build_seconds": build_seconds, "game_compilation_seconds": game_seconds,
                "public_nodes": len(game.nodes), "infosets": len(game.infosets),
                "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "source_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    summaries = []
    # Rotate order across seeds to reduce consistent ordering/thermal bias.
    for index, seed in enumerate(args.seeds):
        methods = args.methods[index % len(args.methods):] + args.methods[:index % len(args.methods)]
        for method in methods:
            summaries.append(run_one(game, method, seed, args.seconds, args.eval_every,
                                     args.output / f"{method.replace(':', '-')}-{seed}", state, policy))
            (args.output / "summary.json").write_text(json.dumps(summaries, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
