# Sampled regret-weighting and variance-reduction experiments

`experimental_sampling.SampledVariant` and `sampled_variants_kernel` implement
four isolated alternatives: `plain`, `linear`, `vr`, and `vr-linear`.
They use the production game tree and Python-compatible random stream. They
are experiments, not additional production checkpoint formats.

`linear` multiplies each regret increment and each sampled strategy-sum
increment by the global iteration number, starting at one. Regret matching is
invariant to a common positive table scale. This is equivalent to adding the
ordinary increment and multiplying both cumulative tables by `t/(t+1)` after
iteration `t`; the stored discounted table is the weighted sum divided by
`t+1`. It discounts early mistakes without clipping noisy sampled regrets.

`vr` keeps a baseline per public node and hidden rank deal, expressed in
player-zero payoff units. At an opponent node it samples action `A` with
probability `p(A)` and returns

`sum_a p(a) b(a) + (sampled_value(A) - b(A))`.

Conditioning on the training history, this has expectation
`sum_a p(a) E[sampled_value(a)]` for any finite baselines: the expected baseline
residual cancels. The usual `p(A)/q(A)` factor is one because `q=p` here.
Baselines are captured before descending into the sampled child, then updated
with an exponential moving average after its return. The updating player's
actions remain fully enumerated, and chance remains sampled without a chance
baseline. This is a partial variance-reduction experiment, not every feature
of the VR-MCCFR paper. The default baseline update rate is 0.5.

Baselines have access to the simulator's hidden deal, as do training action
values; they never become an input to the deployed policy. Action selection
still depends only on an information-set strategy. The estimator remains
unbiased, but these implementation choices need empirical evaluation.

Correctness checks include production-estimator parity with zero baselines,
linear-vs-discounted update equivalence, identical states across split batches,
an exact weighted-expectation check with deliberately inaccurate baselines,
and zero opponent-action variance with a perfect baseline in a small fixture.
The baseline sidecar persists across `advance` calls. Exported experimental
states are archival artifacts; a general restore API is not implemented.

References:

- [Brown and Sandholm, discounted regret minimization](https://arxiv.org/abs/1809.04040).
- [Schmid et al., variance-reduced MCCFR](https://arxiv.org/abs/1809.03057).

Run a timed comparison using the common harness:

```bash
/usr/bin/python3 -S -m game_engine.training.experiment_sweep \
  --methods external sampled-linear sampled-vr sampled-vr-linear \
  --seconds 60 --eval-every 10 --seeds 7 42 2718 \
  --output /tmp/leduc-sampling-comparison
```

The common harness includes transfer, process startup, baseline I/O, exact
evaluation and initialization in the measured run time. Compilation and final
artifact writes are reported separately or excluded, as described in its
metadata. Learning curves show observed checkpoints, not interpolated threshold
crossing times.
