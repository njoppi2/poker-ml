# Expanding the card space

The research game can now vary its rank count and optionally deal a second
public card. The default `ranks=3, public_cards=1` preserves the original
two-street modified Leduc game. `public_cards=2` adds a turn street; information
sets include both revealed board cards and showdown uses both. Setting
`ranks=5` uses `T,J,Q,K,A` instead of `Q,K,A`. The deck still has two copies of
each rank, one private card per player, and no suits, so this remains a
controlled Leduc-like game rather than Texas Hold'em.

The smallest useful run can be made from the full-traversal CFR harness:

```bash
python -m game_engine.training.experimental_cfr \
  --chips 14 --bet-sizes 7 14 --public-cards 2 --ranks 5 \
  --variant dcfr --backend native \
  --iterations 1000 --block 100 --output /tmp/leduc-turn-dcfr
```

The run below used 14 chips and a reduced bet menu `(7, 14)` (a bet target at
7 chips and all-in in cumulative integer-bet units) so exact traversal and
exploitability evaluation stay cheap. It ran the native Rust full-traversal
DCFR kernel; `train_seconds` excludes exact evaluation.

| Iterations | Exploitability (ante units/hand) | Training seconds |
|---:|---:|---:|
| 0 | 2.75690 | 0.000 |
| 100 | 0.007686 | 0.194 |
| 250 | 0.001050 | 0.446 |
| 500 | 0.000302 | 0.831 |
| 1,000 | 0.0000928 | 1.512 |

This compilation had 540 weighted rank deals, 149 public-tree nodes, and 6,540
information sets. The larger rank space remains practical for exact evaluation
with this small bet menu. It does **not** show that the game with every bet size
is similarly small, nor does low exploitability here imply low exploitability
in Hold'em. A prior 10-iteration Python smoke test on 5 chips, 3 ranks, and the
full `(2, 3, 4, 5)` bet menu reduced exploitability from `1.28160` to `0.27186`,
with 1,327 public nodes and 12,480 information sets; that was only a feasibility
check.

The `public_cards` and `ranks` settings are recorded in full-CFR checkpoints,
so a checkpoint cannot accidentally be resumed under different card rules.
The original one-card, three-rank game remains the default. The suit-aware
two-card variant below is separate so its different deal and hand-evaluation
rules cannot alter the existing training baseline.

## Suit-aware two-card mini Hold'em

The next rung is implemented separately as `MiniHoldemGame`: each player gets
two private cards, three community cards are revealed together as a flop, and
there are preflop and flop betting rounds. Its 12-card deck has six ranks
(`9` through `A`) and two suits. That is enough to exercise pairs, two pair,
straights, flushes, and straight flushes while keeping exact chance enumeration
possible. The game ends after the flop, so this is a research stepping stone,
not full Texas Hold'em.

Run it with an all-in-only menu (two legal decisions: check/fold or continue):

```bash
python -m game_engine.training.experimental_cfr \
  --game mini-holdem --chips 2 --bet-sizes 2 \
  --variant dcfr --backend native --iterations 25 --block 5 \
  --output /tmp/mini-holdem-dcfr
```

| Iterations | Exact exploitability | Training seconds |
|---:|---:|---:|
| 0 | 0.376551 | 0.000 |
| 5 | 0.024134 | 0.620 |
| 10 | 0.002491 | 1.227 |
| 25 | 0.000241 | 2.381 |

This game has 166,320 equally weighted physical deals, 22 public-tree nodes,
and 63,690 information sets. Exact evaluation took a few seconds per
checkpoint; training times above exclude evaluation. It confirms that the
native full-traversal kernel can train a suit-aware, two-private-card game
exactly at this very small betting depth. The all-in-only menu and two-suit
deck keep the action tree and card space deliberately constrained.

## Full board with sampled CFR

The next game is implemented as `SampledHoldemGame`: two private cards, a
three-card flop, turn, and river, with betting on all four streets. It keeps
the six-rank/two-suit deck but no longer enumerates chance outcomes into every
node. There are 3,326,400 canonical deals; the public betting tree for four
chips and bet targets `(2, 4)` has 272 nodes. `ExternalSamplingHoldemCFR`
samples one deal and opponent actions each iteration, then adds information
sets as they are encountered.

```bash
python -m game_engine.training.sampled_holdem \
  --chips 4 --bet-sizes 2 4 --iterations 20000 \
  --eval-every 5000 --eval-samples 512 --seed 7 \
  --output /tmp/sampled-holdem
```

The training curve below used one fixed 512-deal evaluation set (seed 2026);
training times exclude evaluation.

| Iterations | Sampled exploitability estimate | Training seconds | Visited information sets |
|---:|---:|---:|---:|
| 0 | 0.970905 | 0.000 | 0 |
| 100 | 0.966372 | 0.031 | 3,567 |
| 500 | 0.933518 | 0.152 | 16,085 |
| 1,000 | 0.889968 | 0.326 | 31,429 |
| 5,000 | 0.828455 | 1.731 | 146,306 |
| 10,000 | 0.813884 | 3.428 | 276,598 |
| 20,000 | 0.756029 | 6.814 | 497,568 |

Three independent 512-deal evaluation samples after 20,000 iterations gave
estimates from `0.721645` to `0.756029`. These are diagnostics, not exact
exploitability certificates: the best response is exact only for each finite
sample and can overfit its deals. The decline suggests learning is happening,
but the remaining estimate is high and the unseen information sets are still
numerous. This is now a useful testbed for reducing sampling variance,
improving average-strategy coverage, and comparing MCCFR variants. A standard
52-card game will need abstraction or function approximation on top of
sampling; this tiny deck is not a claim of full Hold'em strength.

## Coarse-to-fine bet-size curriculum

To make the betting problem larger while keeping the same cards, board, and
rules, the next test used a six-chip stack and expanded only the bet menu:

| Stage | Bet sizes | Public nodes |
|---|---|---:|
| Coarse | 4, 6 | 272 |
| Medium | 2, 4, 6 | 1,032 |
| Fine | 2, 3, 4, 5, 6 | 9,488 |

At each expansion, the coarse average strategy was projected onto the matching
fine histories. Each old action's probability was split among the closest
fine-grained actions with the same role; no probability mass was duplicated.
The expanded solver gave those rows a short average-strategy prior and small
initial regrets. New histories first encountered only after expansion start
from the solver's ordinary uniform initialization. Every transferred
information set in this run matched an information set in the next game.

We compared this schedule (500, 500, then 100 iterations) with 700 iterations
directly in the fine game. Both were evaluated on the same three fixed sets of
128 sampled deals. Mean empirical exploitability was 2.045 for the curriculum
and 2.206 for direct training, about a 7% reduction. Training took about 0.53s
and 0.59s respectively on this run. The curriculum had 1,100 iterations
because the coarse stages were cheaper per iteration. This is a promising
small signal, not a conclusion: best responses are exact only over each
128-deal evaluation sample, and the six-rank/two-suit game is still far from
standard Hold'em.

Reproduce with:

```bash
python -m game_engine.training.experiment_sampled_curriculum \
  --chips 6 --direct-iterations 700 --stage-iterations 500 500 100 \
  --eval-samples 128 --eval-seeds 2026 2027 2028 \
  --output /tmp/sampled-holdem-curriculum
```

The trainer remains vanilla external-sampling MCCFR, not DCFR. This experiment
tests whether action-resolution warm starts help in the larger sampled game;
it does not yet test DCFR discounting on top of MCCFR.

## Full-deck stress test

The sampler now also supports all 13 ranks and four suits. The following run
uses the complete 52-card deck, four betting streets, a 14-chip stack, and a
five-size menu `(2, 5, 8, 11, 14)`. That is about 55.6 trillion canonical
physical deals under the game's no-burn-card rules, so chance sampling is
essential. The public betting tree remains 9,488 nodes; the information-set
space is where the hard growth appears.

On the same three 128-deal evaluation sets, direct fine-game training for 700
iterations estimated exploitability at 5.975, 6.062, and 6.006 chips. The
three-stage curriculum trained for 1,100 iterations in less time (0.49s vs
0.64s) and estimated 5.976, 6.059, and 6.004 chips. Thus the curriculum
reduced compute for essentially the same measured result; it did not improve
the final strategy in this larger game.

Training the fine game for 5,000 iterations took 4.87s and encountered 644,122
information sets, but the three sampled exploitability estimates remained
5.999, 6.083, and 6.031 chips. Given the sample-based evaluator, this is not a
proof of a plateau. It does show the current plain external-sampling MCCFR
setup is not making a clear improvement at this budget, even though it can
process the full deck. This is a concrete next optimization challenge:
improve sampling coverage or variance, and test sampled DCFR, before assuming
that simply running longer will help.

Reproduce the curriculum comparison with:

```bash
python -m game_engine.training.experiment_sampled_curriculum \
  --chips 14 --ranks 13 --suits 4 --bet-sizes 2 5 8 11 14 \
  --direct-iterations 700 --stage-iterations 500 500 100 \
  --eval-samples 128 --eval-seeds 2026 2027 2028 \
  --output /tmp/sampled-holdem-52card-14stack
```
