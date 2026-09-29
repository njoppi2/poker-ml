# Poker research progress and lessons

This file is the short handoff for someone opening the research work after a
clone or pull. It summarizes what was built, what the tests say, and what is
still unproven. The linked experiment notes contain methods, commands, and
full tables.

## Current research games

- **Modified Leduc:** the original compact, two-street game. Its complete game
  tree supports exact exploitability and head-to-head evaluation. This is where
  full-traversal DCFR, CFR variants, and exact exploiter-training ideas were
  tested.
- **Mini Hold'em:** two private cards, a three-card flop, and two betting
  streets on a small suited deck. Exact enumeration is feasible only with a
  very small betting menu.
- **Sampled full-board Hold'em:** two private cards, flop, turn, river, and
  betting on all four streets. It can use the full 52-card deck while sampling
  chance, with a 14-chip stack and five abstract bet sizes `(2, 5, 8, 11, 14)`.
  This is a full-deck research abstraction, not a complete or solved no-limit
  Texas Hold'em game. The 52-card deal space is much too large to enumerate.

## What worked

- **Measure quality at equal wall time and in the final game.** Iteration
  counts are not comparable when one iteration traverses a whole tree and
  another samples a hand. For modified Leduc, exact exploitability gave a
  reliable comparison. For the full-board game, the current evaluator computes
  best response only on a fixed sample of deals, so its estimate is noisier and
  can overfit that sample.
- **Use the right solver for the game size.** On the 12-chip modified-Leduc
  benchmark, native full-tree DCFR reached `0.000447–0.000592 BB/hand` in about
  60 seconds, versus `0.007548–0.008620` for external-sampling MCCFR. This is
  strong evidence for DCFR on that compact game, not evidence that full-tree
  traversal scales to Hold'em.
- **Rust helped the sampled hot loop.** Allocation reduction improved the
  median 100,000-iteration Rust kernel time from `1.3913s` to `0.7921s` (about
  `1.76x`) with exact state parity on the measured inputs. A `target-cpu=native`
  build did not add a reliable speedup. See
  [Rust optimization](rust-optimization.md).
- **Action curricula can save compute, but have not reliably improved the
  strategy.** The full-board, 52-card, 14-chip run reached almost the same
  sampled exploitability after coarse-to-fine training in `0.49s` as direct
  training did in `0.64s`. That is a useful efficiency signal; the final
  strategy scores were effectively tied. In the compact exact Leduc tests,
  direct fine-game DCFR often finished ahead of curricula, with one favorable
  intermediate-stage run that needs replication. See
  [action curriculum on Leduc](action-curriculum.md) and
  [sampled Hold'em expansion](second-public-card.md).
- **A fresh exploiter can help refine a mature policy in some runs.** The best
  evidence is a small late-stage improvement from a strong checkpoint. It did
  not reliably beat continued MCCFR from less mature checkpoints, and the
  tested adversarial variants are not replacements for CFR/DCFR.

## What did not work reliably

- **More iterations alone are not a guarantee.** On compact Leduc, one native
  full-tree DCFR run matched or slightly beat the old 100M-iteration Rust
  policy in exact exploitability at about 990 iterations. The old MCCFR run
  took about 15 minutes for 100M iterations, while a linear projection put 100M
  full-tree DCFR iterations near 39 days. The iteration counts describe very
  different work; the practical result was that the Leduc target did not
  require 100M DCFR iterations.
- **Beating one frozen exploiter is a bad stopping rule.** One update made the
  policy a winner against its current exploiter while its exact exploitability
  rose from `0.001513` to `0.002342`; continued training pushed it to `0.066623`.
  The policy overfit that response and became easier for a newly computed best
  response to exploit.
- **League, simultaneous co-learning, and mixtures did not show a robust win.**
  Keeping stale opponents allowed overfitting; the co-learning prototype failed
  to track a fresh exact best response; tested mixtures of related policies
  were worse than the strongest member. These results do not rule out a more
  diverse population or better update rules, but those ideas need equal-time
  controls and fresh exploitability checks.
- **The current sampled solver is not yet converging convincingly in the larger
  game.** With the full deck, 14-chip stack, and five bet sizes, 5,000 plain
  external-sampling iterations visited about 644,000 information sets in
  `4.87s`; three 128-deal exploitability estimates remained around six chips.
  This is a warning signal, not a proof of a plateau: evaluation uses a small
  deal sample and the information space remains sparsely covered.

## Recommended next work

1. Keep the full-deck, four-street, 14-chip game as the stress test and retain
   the smaller exact Leduc game as a correctness and regression benchmark.
2. Improve the full-board metric first: evaluate on larger held-out deal sets
   and report variation across several fixed seeds before treating small score
   changes as real.
3. Compare sampled DCFR-style discounting and variance-reduction methods
   against plain external-sampling MCCFR at equal wall time. The prior sampled
   variance-reduction pilot on Leduc did not improve its short-run result, so
   test again on the larger game rather than assuming it will help.
4. Retain action curricula only if their compute savings persist under these
   stronger evaluations. The coarse strategy must always be assessed in the
   final action-resolution game.
5. Keep exact exploitability or fresh best-response checks in any exploiter
   training loop. Winning against the current frozen exploiter alone is not a
   safe stopping criterion.

## Experiment index

- [Optimization sweep and adversarial results](optimization-sweep-results.md)
- [When DCFR matched the 100M MCCFR model](dcfr-time-to-beat-100m.md)
- [Full-traversal CFR variants and verification](cfr-variants.md)
- [Exact exploiter-training prototypes](adversarial.md)
- [Action-resolution curriculum on modified Leduc](action-curriculum.md)
- [Card-space, full-board, and sampled curriculum experiments](second-public-card.md)
- [Sampled regret weighting and variance reduction](sampled-variants.md)
- [Rust kernel timing and parity](rust-optimization.md)
