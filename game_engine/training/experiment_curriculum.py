"""Equal-wall-time action-resolution curriculum against direct fine-game DCFR.

Every observation is exact exploitability in the final, full betting game.
Shared game compilation and Rust build are excluded from both training clocks.
Initialization, policy transfer, Rust process calls, and evaluation are included.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import time
from pathlib import Path

from .action_curriculum import lift_policy, transfer_dcfr
from .evaluate import evaluate
from .experimental_cfr import NativeFullTraversalCFR, build_full_cfr_kernel
from .game import LeducGame


def _record(game, solver, source_game, stage, start, rows, output, coverage=None):
    began = time.perf_counter()
    policy = solver.average_policy()
    transfer_coverage = coverage
    if source_game is not game:
        policy, coverage = lift_policy(source_game, game, policy)
    metrics = evaluate(game, policy)
    row = {"stage": stage, "iteration": solver.iterations,
           "elapsed_seconds": time.perf_counter() - start,
           "observation_seconds": time.perf_counter() - began,
           "coverage": coverage, "transfer_coverage": transfer_coverage, **metrics}
    rows.append(row)
    with (output / "metrics.jsonl").open("a") as handle:
        handle.write(json.dumps(row, allow_nan=False) + "\n")
    print(json.dumps(row, allow_nan=False), flush=True)
    return policy, row["observation_seconds"]


def _finish_fine(game, solver, stage, start, seconds, eval_every, rows, output):
    next_eval = max(eval_every, math.ceil((time.perf_counter() - start) / eval_every) * eval_every)
    last_eval = rows[-1]["observation_seconds"]
    block, per_iteration = 25, None
    while True:
        elapsed = time.perf_counter() - start
        remaining = seconds - elapsed - last_eval
        if remaining <= 0:
            break
        if elapsed + last_eval >= next_eval:
            _, last_eval = _record(game, solver, game, stage, start, rows, output)
            next_eval += eval_every
            continue
        allowance = min(3.0, remaining, next_eval - elapsed - last_eval)
        if per_iteration is not None:
            block = max(1, min(200, int(allowance / per_iteration)))
        began = time.perf_counter()
        solver.advance(block)
        per_iteration = (time.perf_counter() - began) / block
    if rows[-1]["iteration"] != solver.iterations or rows[-1]["stage"] != stage:
        policy, _ = _record(game, solver, game, stage, start, rows, output)
    else:
        policy = solver.average_policy()
    return policy


def _run(game, schedule, seconds, eval_every, coarse_iterations, medium_iterations, output):
    output.mkdir()
    start = time.perf_counter()
    rows = []
    if not schedule:
        solver = NativeFullTraversalCFR(game, "dcfr")
        try:
            _record(game, solver, game, "fine_initial", start, rows, output)
            policy = _finish_fine(game, solver, "fine", start, seconds, eval_every, rows, output)
        finally:
            solver.close()
    else:
        current_game = schedule[0]
        solver = NativeFullTraversalCFR(current_game, "dcfr")
        try:
            for stage_index, next_game in enumerate((*schedule[1:], game)):
                iterations = coarse_iterations if stage_index == 0 else medium_iterations
                solver.advance(iterations)
                next_solver, coverage = transfer_dcfr(current_game, next_game, solver)
                solver.close()
                solver = next_solver
                current_game = next_game
                is_fine = current_game is game
                label = "fine_initial" if is_fine else f"resolution_{stage_index + 2}_initial"
                _record(game, solver, current_game, label, start, rows, output, coverage)
                if is_fine:
                    policy = _finish_fine(game, solver, "fine", start, seconds,
                                          eval_every, rows, output)
        finally:
            solver.close()
    (output / "policy.pkl").write_bytes(pickle.dumps(policy, protocol=pickle.HIGHEST_PROTOCOL))
    summary = {"schedule": [list(stage.bet_sizes) for stage in schedule] if schedule else [],
               "budget_seconds": seconds, "coarse_iterations": coarse_iterations,
               "medium_iterations": medium_iterations, "final": rows[-1],
               "best_observed_exploitability": min(row["exploitability"] for row in rows),
               "timing": "includes transfer, training and all exact fine-game evaluations; excludes shared compilation"}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chips", type=int, default=14)
    parser.add_argument("--seconds", type=float, default=45)
    parser.add_argument("--eval-every", type=float, default=10)
    parser.add_argument("--coarse-iterations", type=int, default=5000)
    parser.add_argument("--medium-iterations", type=int, default=5000)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--methods", nargs="+",
                        choices=("direct", "narrow", "broad", "dense", "five", "five_nine",
                                 "five_eight"),
                        default=("direct", "narrow", "broad", "dense"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if (args.output.exists() or not math.isfinite(args.seconds) or args.seconds <= 0 or
            not math.isfinite(args.eval_every) or args.eval_every <= 0 or
            args.coarse_iterations < 0 or args.medium_iterations < 0):
        parser.error("use a new output directory, positive time budgets, and nonnegative iteration counts")
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {args.cpu})
    args.output.mkdir(parents=True)
    build_start = time.perf_counter()
    build_full_cfr_kernel()
    fine = LeducGame(args.chips)
    midpoint = max(2, args.chips // 2)
    narrow = (LeducGame(args.chips, (args.chips,)),
              LeducGame(args.chips, tuple(sorted({midpoint, args.chips}))))
    broad = (LeducGame(args.chips, tuple(sorted({2, midpoint, args.chips}))),
             LeducGame(args.chips, tuple(sorted({2, max(2, args.chips // 3), midpoint,
                                                max(midpoint + 1, args.chips - 4), args.chips}))))
    dense_bets = tuple(sorted(set(range(2, args.chips + 1, 2)) | {args.chips}))
    dense = (LeducGame(args.chips, dense_bets),
             LeducGame(args.chips, tuple(sorted(set(dense_bets) |
                                                  {bet for bet in (3, 7, 11) if bet <= args.chips}))))
    five_bets = tuple(sorted({2 + round(i * (args.chips - 2) / 4) for i in range(5)}))
    nine_bets = tuple(sorted(set(five_bets) |
                             {bet for bet in (3, 6, 9, 12) if bet <= args.chips}))
    eight_bets = tuple(sorted(set(five_bets) |
                              {bet for bet in (3, 7, 12) if bet <= args.chips}))
    five, five_nine = ((LeducGame(args.chips, five_bets),),
                       (LeducGame(args.chips, five_bets), LeducGame(args.chips, nine_bets)))
    five_eight = (LeducGame(args.chips, five_bets), LeducGame(args.chips, eight_bets))
    metadata = {"args": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "shared_build_seconds": time.perf_counter() - build_start,
                "fine_public_nodes": len(fine.nodes), "fine_infosets": len(fine.infosets),
                "fine_actions": sum(len(info.actions) for info in fine.infosets)}
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    summaries = {}
    for name, schedule in (("direct", ()), ("narrow", narrow), ("broad", broad),
                           ("dense", dense), ("five", five), ("five_nine", five_nine),
                           ("five_eight", five_eight)):
        if name not in args.methods:
            continue
        summaries[name] = _run(fine, schedule, args.seconds, args.eval_every,
                               args.coarse_iterations, args.medium_iterations, args.output / name)
        (args.output / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")


if __name__ == "__main__":
    main()
