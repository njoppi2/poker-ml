# Exact adversarial-training experiments

`game_engine.training.experimental_adversarial` is a small, reproducible Leduc
prototype for the idea of training against freshly refreshed exploiters while
retaining earlier exploiters.  It deliberately does not modify the production
trainer, the CFR implementations, or the established benchmark.

## Algorithms

`ed` is the sound baseline: exact tabular Exploitability Descent (ED) in the
compiled Leduc game.  At iteration `t`, first compute an information-set best
response `b_0(pi_1)` and `b_1(pi_0)`.  Then, for player `i` and every
information set `I`, compute the counterfactual action vector

`q_i^c(I, a) = sum_(h in I) eta_-i(h) q_i(h, a)`

against the other seat's fresh best response.  Here `eta_-i` includes chance
and opponent reach but omits the updating player's reach.  Both seats are
updated synchronously from the same deployed policy:

`pi_i^t(I) = Projection_simplex(pi_i^(t-1)(I) + alpha / sqrt(t) * q_i^c(I))`.

The implementation exposes best-response choices and their unnormalised
counterfactual action scores, and evaluates only the deployed joint policy
with an exact hidden-information-safe best response.  It is a direct tabular
prototype of projected ED, not an MCCFR loop with a different sampled
opponent.  The latter substitution does not retain MCCFR's convergence claim.

`league` implements the requested applied experiment separately.  Every
`refresh_every` updates it creates exact P0 and P1 exploiters of the current
deployed policy, retains the newest `max_snapshots` pairs, and trains each
seat against whole current-self-play or whole frozen opposing policies on a
deterministic weighted rotating schedule.  It does not mix action rows: doing
so would change the correlation of an opponent's actions across a hand.  Its
local updates still use exact counterfactual reach weights and update both
seats synchronously, but the frozen-pool schedule and eviction rule are
heuristic.  Do not attribute CFR, ED,
PSRO, or league-training convergence guarantees to this mode.

The sweep also exposes a **single-exploiter** version of the league as
`single:step:refresh:self_play_weight`, with `max_snapshots=1`. With
`refresh=1` and `self_play_weight=0`, its updates match ED exactly; a native
regression test checks this. Larger refresh intervals hold one best response
fixed while the deployed policy takes multiple updates. The `self_play_weight`
controls how many *whole updates* use self-play instead of the exploiter.

`batch:step:refresh:self_play_weight` tests a related idea: in *each* update,
compute counterfactual action scores against the current single exploiter and
against the deployed policy itself, average those scores using the indicated
self-play weight, then make one projected policy update. This averages two
complete-opponent objectives; it does not mix their action rows within a hand.
It is a heuristic experiment without a convergence claim. A small-game test
checks the native batch update against separately computed Python scores.

`colearn:step:refresh:self_play_weight:exploiter_step_multiplier` keeps that
single exploiter pair as two tabular learning policies. It starts from an exact
best response, then both the deployed policy and each exploiter take a
projected counterfactual update from the *same prior state*. The deployed
policy batches exploiter and self-play scores; each exploiter learns against
the deployed policy. `refresh` can periodically reset exploiters to exact
best responses. With a very large refresh interval, they learn continuously
without being replaced. The multiplier controls the exploiter's update size
relative to the deployed policy. This is a deliberately simple coupled
learner, not a convergence-guaranteed algorithm; its Rust update has an
independent Python parity test.

`counterbatch:step:responses:self_play_weight[:response_growth]` tests a short
look-ahead batch.
From the deployed policy `p`, find an exact response pair, take a *provisional*
ED step, and repeat for `responses` pairs. Then discard the provisional policy
and average the counterfactual scores of all response pairs evaluated against
the original `p`. One projected update changes `p`. An optional self-play
weight mixes in the original policy's self-play scores. Optional
`response_growth` gives successive responses geometric weights
`1, growth, growth^2, ...`; it defaults to 1 for an equal batch. With one
response and zero self-play weight this is exactly ED. The provisional steps
use the same step size as the final update. This is a heuristic response-diversification
experiment, not a convergence-guaranteed algorithm. A small-game test checks
the reset-and-batch operation against an independent Python calculation.

`CFRBestResponse` is a separate exact CFR-BR reference implementation.  Each
iteration computes fresh best responses to the two current regret-matched
policies, adds the resulting counterfactual regrets for both seats, and exports
the chance-weighted own-realization average policy.  It has no ED step-size;
use it to distinguish an ED hyperparameter issue from the fresh-exploiter idea.

## Run and budget

Use a dedicated new output directory; the CLI refuses to overwrite one:

```bash
python -m game_engine.training.experimental_adversarial \
  --algorithm ed --chips 4 --iterations 5000 --eval-every 100 \
  --output /home/njoppi2/Documents/Codex/2026-09-24/hey-i-want-you-to-take/outputs/optimization-sweep/adversarial/ed-5000

python -m game_engine.training.experimental_adversarial \
  --algorithm league --chips 4 --iterations 5000 --step-size 0.25 \
  --refresh-every 25 --max-snapshots 8 --self-play-weight 0.5 --eval-every 100 \
  --output /home/njoppi2/Documents/Codex/2026-09-24/hey-i-want-you-to-take/outputs/optimization-sweep/adversarial/league-5000
```

For a wall-clock cap, pass `--time-budget-s 60` along with an iteration upper
bound.  Each run writes `metrics.jsonl`, `policy.json`, and `summary.json`.
`metrics.jsonl` reports exact `best_response_p0`, `best_response_p1`,
`nash_conv`, and `exploitability` of the deployed policy; compare those values
and elapsed seconds across algorithms, not their iteration counts.

To warm-start directly from a trusted `policy.pkl` emitted by the existing
benchmark, pass `--initial-policy /path/to/policy.pkl`.  The initial policy is
the deployed policy at metric iteration zero.  In league mode the first fresh
exploiters are generated from it, but it is never replaced by them; only the
subsequent scheduled whole-opponent update changes it.  Both trainers also offer the
small common programmatic interface `advance(n)`, `average_policy()` (an alias
for the current deployed policy), and `iterations`.

`NativeTabularED`, `NativeHeuristicLeague`, and `NativeCFRBestResponse` expose
the same interface and execute the exact tree passes in the separate
`adversarial_kernel` Rust crate.  Native CFR-BR has no warm-start argument. It
is tested for uninterrupted versus split-batch equivalence and exact small-game
improvement. Strict Python/native table parity is run only before Python 3.12,
whose changed floating summation can choose a different exact-BR tie.

Smoke check:

```bash
python -m unittest tests.test_training_adversarial -v
```

## Sources and limits

Lockhart et al., [Computing Approximate Equilibria in Sequential Adversarial
Games by Exploitability Descent](https://arxiv.org/abs/1903.05614), describe
ED, its counterfactual values, and the projected-simplex tabular update.
Heinrich, Lanctot and Silver, [Fictitious Self-Play in Extensive-Form
Games](https://proceedings.mlr.press/v37/heinrich15.html), gives the extensive-form fictitious
play reach-weighting context.  Lanctot et al., [A Unified Game-Theoretic
Approach to Multiagent Reinforcement Learning](https://arxiv.org/abs/1711.00832),
introduces the PSRO framing for policy pools and meta-solvers.

The experiment enumerates this repository's compact Leduc tree exactly.  It
does not establish scalability, approximate-best-response robustness, neural
function-approximation behavior, or a policy-pool convergence result.  Ties
in zero-reach information sets are deterministically resolved by action order;
they cannot change the exact response value.
