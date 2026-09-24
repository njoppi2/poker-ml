# Modified Leduc training and convergence

The benchmark answers "how much computation buys a given strategy quality?" for
the original research game. It does not train Hold'em or replace the app's model.
It uses only Python's standard library; OpenSpiel is an optional validation dependency.

## Run

From the repository root:

```bash
python3 -m game_engine.training.benchmark \
  --chips 12 --algorithms external legacy --seeds 42 43 44 \
  --iterations 100000 --eval-every 5000 --max-seconds 30 \
  --output artifacts/training-runs/comparison
```

Each seed/algorithm has its own 30-second **training** budget (checked every 100
iterations, so a small overrun is possible). Compilation, exact evaluation and
checkpoint writes take additional time, recorded separately. There is no work
in the background after the command exits. An existing output directory is
rejected rather than overwritten. Use a new directory for each experiment.

For a quick check, use `--chips 4 --iterations 2000 --eval-every 500`.
For stopping on quality, add `--target 0.25`. This stops at the first evaluated
checkpoint with exploitability at or below 0.25 BB/hand, not at a proof of equilibrium.

Outputs:

- `metadata.json`: parameters, game size, Python/platform, Git revision/dirty state
  and source-file SHA-256 hashes.
- `<algorithm>-<seed>/metrics.jsonl`: exact exploitability, best responses,
  self-play value, training time, evaluation time, iterations and node visits.
- `<algorithm>-<seed>/checkpoint.pkl`: regrets, averaging accumulators, RNG state
  and iteration count; sufficient to resume identical updates.
- `<algorithm>-<seed>/policy.pkl`: average strategy in the historical blueprint
  format. This is a separate file; the runtime blueprint remains unchanged.
- `summary.json`: final measured quality and reason each run stopped.

Resume to a **total**, not an additional, iteration count:

```bash
python3 -m game_engine.training.benchmark \
  --resume artifacts/training-runs/comparison/external-42/checkpoint.pkl \
  --iterations 200000 --eval-every 10000 --target 0.25 \
  --output artifacts/training-runs/resumed
```

A new `--max-seconds` budget applies to the resumed segment. Training times remain
cumulative. Resuming preserves the seed and algorithm; incompatible stack sizes
and iteration ceilings are rejected. Pickles can execute code: load only trusted
local models/checkpoints. Old average-strategy-only blueprints cannot resume
training because they contain neither regrets nor RNG state.

Evaluate the saved research policy without retraining:

```bash
python3 -m game_engine.training.benchmark \
  --evaluate-blueprint game_engine/models/runtime/IOu-mccfr-6cards-11maxbet-EPcfr0_0-mRW0_0-iter100000000.pkl \
  --missing call --output artifacts/training-runs/saved-model
```

`--missing call` completes absent entries with legal call/check actions, matching
the runtime's intended fallback. `--missing uniform` measures sensitivity to this
choice. The report includes the missing-state count; it is not a measurement of
the websocket engine's edge-case behavior.

## What is measured

This is the project's modified heads-up Leduc: Q/Q/K/K/A/A, equal one-unit antes,
one private card per player, one public card, two streets, integer cumulative
bets up to the starting stack, and the historical forced `-` transition that
makes player zero start the flop. It preserves the historical betting rules,
including their differences from standard limit Leduc or casino no-limit rules.
Do not compare these numbers directly to OpenSpiel's built-in `leduc_poker`.

The compiler enumerates the public betting tree once. The full 12-chip game has
28,882 public nodes and 89,979 information sets. It merges 120 physical ordered
card deals into 24 rank triples with their exact probabilities, without leaking
the opponent's card or the unrevealed public card to a policy.

For a policy pair, the evaluator computes both exact best responses. Each best
response chooses one action for an **information set**, aggregating over possible
hidden deals; it cannot choose using the opponent's private card.

- `nash_conv = BR_0 + BR_1` in this zero-sum game.
- `exploitability = nash_conv / 2`, following OpenSpiel's convention.
- Utilities are net ante units per hand. Here an ante is one original big blind;
  multiply BB/hand by 1,000 for milli-big-blinds/hand.
- Lower exploitability is better. Self-play winnings alone do not measure it.
- Evaluation enumerates all outcomes, so there is no match-sampling standard
  error. Training is stochastic: compare multiple training seeds.

The evaluator is exact for this modeled game and the chosen policy completion,
not a claim about all poker games or Nash convergence of the historical trainer.

## Algorithm audit

The historical `mod_leduc.py` sampling traversal is a custom hybrid. Along its
sampled principal path it updates both players; on a deviation it enumerates the
same player's future alternatives and samples the opponent. It then multiplies
updates by the opponent's full reach probability. This is **not** the standard
external-sampling estimator: sampled opponent/chance reach is already represented
by how often the trajectory occurs. Importing full-tree CFR's reach multiplier
without a corresponding sampling-probability correction can double-weight it.
The hybrid also averages strategies on a different visitation schedule. These
facts mean its name alone is not a convergence guarantee; no formal derivation
of that hybrid's estimator is provided here.

The new `external` solver uses two traversals per iteration, one per updating
player: it samples chance and opponent actions, enumerates all updating-player
actions, subtracts their policy-weighted value, and averages at opponent nodes
using the two-player simple estimator. Its updates are checked against OpenSpiel
with identical random samples and matching zero initialization.

The old signed global regret diagnostic allows positive and negative terms to
cancel; it is not NashConv, exploitability, or a stopping certificate. The benchmark
does not use that diagnostic to decide when training is complete.

The `legacy` benchmark adapter preserves the old update semantics, disables log
and snapshot IO inside iterations, and isolates its global random state. It also
counts node visits (a small instrumentation cost). The allocation cleanup skips
constructing nodes that already exist, discards unused list work, and removes a
state transition immediately recomputed by the loop. Fixed-seed accumulated
regrets and average-strategy sums match fixtures from the original trainer.

Iteration counts are **not directly equivalent**: `external` uses two player
traversals and independent deals; `legacy` uses one mixed traversal and one
shuffled deal. Compare time to a target quality and node visits as well as counts.
Neither solver is claiming a parallel/GPU implementation. The compiled tree and
direct information-set indices remove repeated history parsing and legality work
from the new solver's training loop.

## Validation

```bash
python3 -m pip install -e '.[training-reference]'
python3 -m unittest discover -s tests -p 'test_training*.py'
```

The optional reference checks compare exact best responses to OpenSpiel and
compare sampled updates on the same hidden-information game. Normal tests cover
chance weights, payouts, hidden-card information sets, probability validation,
fixed-seed regression, exact checkpoint resumption, stopping and overwrite guards.
Without the optional extra, the reference checks explicitly skip; the remaining
training tests still run. CI installs the extra.

Sources:

- [Lanctot et al., Monte Carlo Sampling for Regret Minimization (2009)](https://bowlingmh.github.io/publications/b2hd-09nips-mccfr-w-trws.html)
- [OpenSpiel external-sampling implementation](https://github.com/google-deepmind/open_spiel/blob/v1.6.11/open_spiel/python/algorithms/external_sampling_mccfr.py)
- [OpenSpiel best-response implementation](https://github.com/google-deepmind/open_spiel/blob/v1.6.11/open_spiel/python/algorithms/best_response.py)

Discounted CFR and other sampling variants are future comparisons, not implemented
or claimed as validated by this benchmark.
