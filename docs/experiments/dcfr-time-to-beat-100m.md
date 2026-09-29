# DCFR time to surpass the 100M models

I trained a fresh native full-tree DCFR policy from a uniform strategy on the
12-chip modified Leduc game. Every 10 iterations I measured exact exploitability
and exact seat-balanced head-to-head value against both 100M policies:

1. The historical saved model, exploitability `0.268708 BB/hand`.
2. The newer Rust external-sampling model, trained to 100M, exploitability
   `0.001512605 BB/hand`.

## First observed crossings

| Criterion | Iteration | Solver training time | Wall time including exact measurements |
|---|---:|---:|---:|
| Lower exploitability than historical model | 40 | 1.95 s | 8.39 s |
| Positive head-to-head vs historical model | 210 | 10.62 s | 39.02 s |
| Lower exploitability than Rust 100M model | 990 | 50.09 s | 180.55 s |
| Positive head-to-head vs Rust 100M model | 970 | 49.07 s | 176.91 s |

“First observed” matters. The candidate's matchup against the historical model
first turned slightly positive at iteration 210, then briefly dipped negative.
It was positive at every measured point from iteration 460 onward. Against the
newer Rust 100M model, the final three points (970, 980, 990) were positive, but
the final margin was only `+0.00323 BB/100`. The exploitability difference at
iteration 990 was also small: `0.00150354` versus `0.00151261`. This is a
near-tie in one deterministic training run, not strong evidence of general
superiority.

The wall time includes exact exploitability plus two exact matchup calculations
every 10 iterations. Those measurements used `126.28 s` by the final point; the
solver itself trained for `50.09 s`. Evaluating less frequently would reduce
wall time while making the stopping point less precise. Exact matchups enumerate
the modeled game, so the result has no hand-sampling error.

## What 100 million iterations would take

Iteration counts represent very different work for these two algorithms:

- **Rust external-sampling MCCFR:** the completed run added 98 million iterations
  in `881.35 s` of recorded training time (14 min 41 s). A 100M run entirely at
  that measured Rust rate would take about **15 minutes of training**.
- **Full-tree DCFR:** three 60-second benchmarks completed 1,625–1,765 iterations
  in 55.75–55.93 s of solver time. Their median throughput projects 100 million
  DCFR iterations to about **39 days of continuous solver time** on this machine.

The DCFR projection is a linear estimate from short runs, not a long-run
measurement. It is also unnecessary for the measured goal: the fresh DCFR policy
was already marginally below the newer 100M model's exploitability by iteration
990. Do not compare iteration counts across MCCFR and DCFR as if they were equal
units of computation.

## Reproducibility and limits

The candidate started from scratch; neither reference policy was used for
training. The tested code is full-tree DCFR `(alpha, beta, gamma) = (1.5, 0, 2)`.
The game is this repository's modified Leduc variant, not Texas Hold'em. This is
one deterministic training trajectory with evaluations every 10 iterations.
DCFR remains an experimental implementation pending an independent recurrence
reference check.

Raw checkpoint metrics and the runner are in the shared task output directory:
`outputs/optimization-sweep/dcfr-time-to-beat/`.
