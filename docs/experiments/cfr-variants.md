# Full-traversal CFR variants

`game_engine.training.experimental_cfr` is an experimental comparison baseline
for the project's compiled modified-Leduc game.  It does not change the
production external-sampling solver.

Each iteration contains chronological player-zero then player-one sweeps.  A
sweep enumerates all 24 weighted rank deals and freezes the current strategy for
that sweep.  At an information set `I`, its regret increment is:

`sum(h in I) chance(h) * pi_-i(h) * (v_i(h, a) - v_i(h))`.

Average strategy accumulation uses `chance(h) * pi_i(h) * sigma_i(I)`.  These
two reach factors are different.  The game compiler maps several hidden deals
to the same information set, so values must be summed before a regret row is
updated.  This is also the property enforced by
`tests/test_training_cfr_variants.py`.

Available variants are `vanilla`, `cfr_plus`, and `dcfr`.  CFR+ applies
`max(0, R + delta)` only in this full-tree implementation and linearly weights
the strategy contribution from iteration `t` by `t`.  DCFR uses the
recommended `(alpha, beta, gamma) = (3/2, 0, 2)`: after completed iteration `t`, positive
regrets are multiplied by `t^alpha/(t^alpha+1)`, negative regrets by
`t^beta/(t^beta+1)`, and cumulative strategy weights by `(t/(t+1))^gamma`.

Run a bounded Python experiment:

```bash
python -m game_engine.training.experimental_cfr --chips 12 --variant dcfr \
  --iterations 10000 --block 100 --max-seconds 30 \
  --output /home/njoppi2/Documents/Codex/2026-09-24/hey-i-want-you-to-take/outputs/optimization-sweep/cfr/dcfr-python
```

`run_blocks` emits `metrics.jsonl` plus `summary.json`.  `train_seconds` covers
only solver advancement; each row separately records exact-evaluation time.
The optional `NativeFullTraversalCFR` is API-compatible and batches blocks into
`cfr_variants_kernel`; its training time includes serialization and process
launch, but excludes compilation, evaluation, and export.

## Verification record

The deterministic test suite uses an independent recursive expected-value
calculation and central finite differences at three early/mid/late information
sets for each player, on a randomized positive 3-chip profile.  It checks the
directional identity
`d u_i / d(sigma(I,0)-sigma(I,1)) = pi_i(I) * (delta(I,0)-delta(I,1))`, and
the separate average-strategy increment.  The observed maximum errors were
`6.93e-11` for the numerical derivative and `2.78e-17` for strategy-sum
increments.

An OpenSpiel `CFRSolver` comparison ran with its cached Python-3.10 build on
the 2-chip game for three alternating iterations.  Cumulative regret rows
matched to `2.22e-16`; normalized average-policy rows matched to `1.11e-16`.
This implementation stores a fixed chance-mass multiple in each information
set's strategy-sum row, whereas OpenSpiel omits that factor.  It cancels when
the row is normalized, so the reported policy is identical.

Sources: Zinkevich et al., *Regret Minimization in Games with Incomplete
Information* (NIPS 2007), section 3; Tammelin, *Solving Large Imperfect
Information Games Using CFR+* (2014), sections 3--4; Brown and Sandholm,
*Solving Imperfect-Information Games via Discounted Regret Minimization* (AAAI
2019), equations 5--7.  These are full-tree update equations.  They should not
be transferred by clipping the current external-sampling MCCFR estimator,
because that estimator samples chance and opponent histories instead of
explicitly carrying their counterfactual reach weights.
