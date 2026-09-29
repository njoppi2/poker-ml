"""Compare direct and coarse-to-fine MCCFR on sampled full-board Hold'em."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .sampled_curriculum import seed_expanded_solver
from .sampled_holdem import ExternalSamplingHoldemCFR, SampledHoldemGame, evaluate_sampled


def _train(game, iterations, seed, solver=None):
    if solver is None:
        solver = ExternalSamplingHoldemCFR(game, seed=seed)
    started = time.perf_counter()
    solver.advance(iterations)
    return solver, time.perf_counter() - started


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chips", type=int, default=6)
    parser.add_argument("--ranks", type=int, default=6)
    parser.add_argument("--suits", type=int, choices=(2, 4), default=2)
    parser.add_argument("--bet-sizes", type=int, nargs="+")
    parser.add_argument("--direct-iterations", type=int, default=700)
    parser.add_argument("--stage-iterations", type=int, nargs=3, default=(500, 500, 100))
    parser.add_argument("--eval-samples", type=int, default=128)
    parser.add_argument("--eval-seeds", type=int, nargs="+", default=(2026, 2027, 2028))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if (args.output.exists() or args.direct_iterations < 0 or args.eval_samples < 1
            or any(iterations < 0 for iterations in args.stage_iterations)):
        parser.error("output must be new; iterations nonnegative; eval-samples positive")
    fine_menu = tuple(args.bet_sizes) if args.bet_sizes else tuple(range(2, args.chips + 1))
    if not fine_menu or fine_menu[-1] != args.chips or tuple(sorted(set(fine_menu))) != fine_menu:
        parser.error("bet-sizes must be sorted, unique, and include the all-in stack size")
    coarse_size = fine_menu[len(fine_menu) // 2]
    coarse_menu = tuple(sorted({coarse_size, args.chips}))
    middle_menu = tuple(sorted({fine_menu[0], coarse_size, args.chips}))
    schedule = (coarse_menu, middle_menu, fine_menu)
    if not (set(coarse_menu) <= set(middle_menu) <= set(fine_menu)):
        parser.error("curriculum menus must be nested; choose at least 4 chips")
    args.output.mkdir(parents=True)

    direct_game = SampledHoldemGame(args.chips, fine_menu, args.ranks, args.suits)
    direct, direct_seconds = _train(direct_game, args.direct_iterations, 101)
    direct_eval = [evaluate_sampled(direct, samples=args.eval_samples, seed=seed)
                   for seed in args.eval_seeds]

    solver = None
    stage_rows, transfer_rows = [], []
    for stage, (menu, iterations) in enumerate(zip(schedule, args.stage_iterations)):
        game = SampledHoldemGame(args.chips, menu, args.ranks, args.suits)
        current = ExternalSamplingHoldemCFR(game, seed=101 + stage)
        if solver is not None:
            transfer_rows.append(seed_expanded_solver(solver, current))
        current, elapsed = _train(game, iterations, 101 + stage, current)
        stage_rows.append({"bet_sizes": menu, "public_nodes": len(game.nodes),
                           "iterations": iterations, "training_seconds": elapsed,
                           "visited_infosets": len(game.infosets)})
        solver = current
    curriculum_eval = [evaluate_sampled(solver, samples=args.eval_samples, seed=seed)
                       for seed in args.eval_seeds]

    result = {
        "game": {"chips": args.chips, "ranks": direct_game.ranks,
                 "suits": direct_game.suits, "streets": direct_game.phases},
        "evaluation": {"samples_per_seed": args.eval_samples, "seeds": args.eval_seeds,
                       "note": "empirical exploitability; best response is exact only within each sampled deal set"},
        "direct": {"bet_sizes": fine_menu, "public_nodes": len(direct_game.nodes),
                   "iterations": args.direct_iterations, "training_seconds": direct_seconds,
                   "visited_infosets": len(direct_game.infosets), "evaluations": direct_eval},
        "curriculum": {"schedule": stage_rows, "transfer": transfer_rows,
                       "training_seconds": sum(row["training_seconds"] for row in stage_rows),
                       "evaluations": curriculum_eval},
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
