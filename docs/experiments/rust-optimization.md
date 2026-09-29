# Rust kernel allocation reduction

The external-sampling kernel now keeps strategy, action-value, and cumulative
sampling scratch data in bounded stack arrays. The public trainer permits at
most 12 chips, yielding at most 12 actions at an information set; Leduc chance
sampling has 24 weighted rank deals (representing 120 physical deals). Chance cumulative weights are built once per
kernel invocation. Sampling still uses the same MT19937 draws, sequential
floating-point accumulation, and binary-search boundary comparisons.

Exact output-state parity against baseline commit `821d862` was checked at 1,
7, and 13 iterations for chips=12, seeds 42 and 7319. A 100,000-iteration
chips=12 seed=7319 input also produced identical output state bytes. Comparisons
excluded only the elapsed-time field. `tests/test_training_rust_optimization.py`
records those short baseline state digests and checks native checkpoint/resume
against an uninterrupted run.

## Timing

Five serial trials per binary used one fixed pre-serialized input (100,000
iterations, chips=12, seed=7319), pinned to CPU 0. One disposable warmup ran
for each binary before the alternating trials. Starting system load was
2.31 / 2.45 / 2.62. Median kernel times were:

| Build | Median | Relative to baseline |
| --- | ---: | ---: |
| Baseline release | 1.3913 s | 1.00x |
| Allocation-reduced release | 0.7921 s | 1.76x |
| Allocation-reduced `target-cpu=native` | 0.7956 s | 1.75x |

The optimized release build reduced median kernel time by about 43%. The native
CPU build showed no median improvement, with two slower noisy trials. Raw wall
and kernel measurements are in
`outputs/optimization-sweep/rust/timings-5x.json` in the shared task output
directory.

To reproduce the native build:

```sh
CARGO_TARGET_DIR=/tmp/leduc-native RUSTFLAGS='-C target-cpu=native' \
  cargo build --release --manifest-path game_engine/training/rust_kernel/Cargo.toml
```

The existing Python/Rust exact-state suite passes under Python 3.10.12
(`PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -S -m unittest discover -s tests -p test_training.py`).
Under Python 3.14.3, a resumed
Python-vs-Rust comparison can differ in the last float bits: the first observed
difference was one ULP in a regret and strategy sum. Running the same sequence
against the saved baseline executable produces the same difference, so it is
not caused by this optimization. The native baseline state fixtures avoid
cross-language reduction differences.
