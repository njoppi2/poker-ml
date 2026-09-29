"""Plot archived sweep outputs (optional dependency: matplotlib)."""
import argparse
import json
from pathlib import Path
from statistics import median


def read_runs(folder):
    runs = []
    for path in sorted(folder.glob("*/metrics.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if rows:
            runs.append(rows)
    return runs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "savefig.facecolor": "white"})
    names = {"external": "Optimized sampled CFR", "sampled-linear": "Sampled CFR, linear weights",
             "full-cfr_plus": "Full-tree CFR+", "full-dcfr": "Full-tree discounted CFR",
             "cfr-br": "CFR against best responses"}
    colors = {"external": "#59687a", "sampled-linear": "#d9862f", "full-cfr_plus": "#169a8b",
              "full-dcfr": "#2460b3", "cfr-br": "#9c4886"}
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5), constrained_layout=True)
    runs = read_runs(args.root / "finalists")
    methods = list(dict.fromkeys(row[0]["method"] for row in runs))
    for method in methods:
        group = [run for run in runs if run[0]["method"] == method]
        # Interpolation is solely for drawing a median trajectory. Threshold
        # timing in the report uses actual observed checkpoints, never this line.
        low = max(run[0]["elapsed_seconds"] for run in group)
        high = min(run[-1]["elapsed_seconds"] for run in group)
        grid = np.linspace(low, high, 150)
        ys = [np.interp(grid, [r["elapsed_seconds"] for r in run],
                        [r["exploitability"] for r in run]) for run in group]
        color = colors.get(method)
        axes[0].plot(grid, np.median(ys, axis=0), label=names.get(method, method), color=color, lw=2)
        axes[0].fill_between(grid, np.min(ys, axis=0), np.max(ys, axis=0), color=color, alpha=0.1)
        for run in group:
            axes[0].scatter([run[-1]["elapsed_seconds"]], [run[-1]["exploitability"]], color=color, s=20)
    axes[0].set_title("Longer comparison: three runs per method")
    axes[0].set_xlabel("Total elapsed seconds, including evaluation")
    axes[0].set_ylabel("Exact exploitability (BB/hand; lower is better)")

    adversarial = (read_runs(args.root / "adversarial-pilot") +
                   read_runs(args.root / "league-cold-pilot"))
    selected = []
    for family in ("ed", "league", "cfr-br"):
        candidates = [run for run in adversarial if run[0]["method"].split(":")[0] == family]
        if candidates:
            selected.append(min(candidates, key=lambda run: run[-1]["exploitability"]))
    pilot = read_runs(args.root / "pilot")
    selected.extend(run for run in pilot if run[0]["method"] in ("external", "full-dcfr"))
    for run in selected:
        method = run[0]["method"]
        label = names.get(method, method.replace("ed:", "ED, step ").replace("league:", "League, step "))
        axes[1].plot([r["elapsed_seconds"] for r in run], [r["exploitability"] for r in run],
                     marker=".", markersize=4, label=label, color=colors.get(method), lw=1.8)
    axes[1].set_title("Exploiter experiments: best screened settings")
    axes[1].set_xlabel("Total elapsed seconds, including opponent generation")
    for ax in axes:
        ax.set_yscale("log")
        ax.grid(True, which="major", alpha=0.18)
        ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("Modified Leduc • 12-chip stacks • exact evaluation", fontsize=15, fontweight="bold")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=170)
    fig.savefig(args.output.with_suffix(".svg"))
    plt.close(fig)

    warm = read_runs(args.root / "warm-start")
    if warm:
        fig, ax = plt.subplots(figsize=(9, 4.5), constrained_layout=True)
        for run in warm:
            method = run[0]["method"]
            label = names.get(method, method.replace("ed:", "ED, step ").replace("league:", "League, step "))
            ax.plot([r["elapsed_seconds"] for r in run], [r["exploitability"] for r in run],
                    marker=".", label=label)
        baseline = warm[0][0]["exploitability"]
        ax.axhline(baseline, color="#444444", ls="--", lw=1, label="Starting 100M policy")
        ax.set(title="Can exploiters improve the existing 100M policy?", xlabel="Total elapsed seconds",
               ylabel="Exact exploitability (BB/hand; lower is better)", yscale="log")
        ax.grid(alpha=0.18)
        ax.legend(fontsize=8)
        fig.savefig(args.output.with_name("warm-start.png"), dpi=170)
        plt.close(fig)

    paired = read_runs(args.root / "warm-100m-control")
    if paired:
        fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
        for run in paired:
            method = run[0]["method"]
            label = "Exploitability descent" if method.startswith("ed:") else "Continued external sampling"
            ax.plot([r["elapsed_seconds"] for r in run],
                    [r["exploitability"] for r in run], marker=".", label=label)
        ax.axhline(paired[0][0]["exploitability"], color="#444444", ls="--", lw=1,
                   label="Starting 100M policy")
        ax.set(title="Paired refinement from the 100M checkpoint", xlabel="Total elapsed seconds",
               ylabel="Exact exploitability (BB/hand; lower is better)", yscale="log")
        ax.grid(alpha=0.18)
        ax.legend()
        paired_output = args.output.with_name("warm-100m-paired.png")
        fig.savefig(paired_output, dpi=170)
        fig.savefig(paired_output.with_suffix(".svg"))
        plt.close(fig)

    frozen_root = args.root / "frozen-exploiter-probe"
    if (frozen_root / "early-checkpoints.json").exists():
        early = json.loads((frozen_root / "early-checkpoints.json").read_text())
        later = [json.loads(line) for line in (frozen_root / "metrics.jsonl").read_text().splitlines()]
        rows = {row["iteration"]: row for row in early + later}
        rows = [rows[iteration] for iteration in sorted(rows)]
        iterations = [row["iteration"] for row in rows]
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), constrained_layout=True)
        axes[0].plot(iterations, [row["exploitability"] for row in rows], marker="o", color="#aa4538")
        axes[0].axhline(early[0]["exploitability"], ls="--", lw=1, color="#666666")
        axes[0].set(title="Risk against a fresh best response", ylabel="Exploitability (BB/hand)")
        axes[1].plot(iterations, [row["vs_frozen_bb_per_100"] for row in rows],
                     marker="o", color="#2460b3")
        axes[1].axhline(0, ls="--", lw=1, color="#666666")
        axes[1].set(title="Payoff against the frozen exploiter", ylabel="BB/100")
        for ax in axes:
            ax.set_xscale("symlog", linthresh=1)
            ax.set_xlim(left=0)
            ax.set_xticks([0, 1, 5, 20, 100, 1000])
            ax.set_xlabel("Policy updates against one frozen exploiter")
            ax.grid(alpha=0.18)
        fig.suptitle("Beating one opponent can increase exploitability", fontweight="bold")
        frozen_output = args.output.with_name("frozen-exploiter-stop.png")
        fig.savefig(frozen_output, dpi=170)
        fig.savefig(frozen_output.with_suffix(".svg"))
        plt.close(fig)


if __name__ == "__main__":
    main()
