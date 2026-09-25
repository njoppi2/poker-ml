# Rust training experiment

## What we learned

- The main cost in the external-sampling Leduc trainer is its recursive Python
  traversal, strategy calculation, and regret/average-strategy updates. Running
  the existing Python code under PyPy helped substantially, but a native kernel
  removed most of that interpreter overhead.
- Keep the game rules and exact evaluator in Python, and pass a flattened public
  game tree plus training state to the Rust kernel. The kernel can reproduce the
  Python MT19937 stream and weighted sampling. Its complete state matched the
  Python solver exactly after both short parity checks and the 100-million run.
- Measure both the kernel and the integrated backend. The isolated release
  kernel took a median 0.413 seconds per 50,000 iterations. Through the trainer
  interface, including state serialization and launching the native process,
  the 98-million iteration continuation took 881.35 seconds of recorded
  training time. The second figure is the useful planning number for this
  implementation.
- The 100-million result belongs to this project's modified Leduc game and
  external-sampling MCCFR. It is not a Texas Hold'em result, and it cannot be
  compared directly with the historical 100-million run, which used another
  training implementation.

## Recorded 100-million run

The Rust backend resumed seed 42 from the existing 2-million-iteration
checkpoint, ran a 1-million-iteration preflight, then continued from 3 million
to a total of 100 million. It wrote a Python-readable checkpoint and exact
exploitability/head-to-head metrics every million iterations.

| Measurement | Result |
|---|---:|
| Final total iterations | 100,000,000 |
| New iterations from the 2M checkpoint | 98,000,000 |
| Recorded training time for those new iterations | 881.35 s (14 min 41 s) |
| Final exact exploitability | 0.0015126 BB/hand |
| Head-to-head versus the historical runtime blueprint | +0.2468 BB/100, seat-balanced |

The head-to-head comparison uses exact game evaluation and the benchmark's
`call` completion for 2,465 information sets absent from the old blueprint.
The Rust checkpoint was loaded through the Python solver, and its saved policy
matched a re-export from that checkpoint.

The isolated 50,000-iteration runtime comparison used the same 2M checkpoint,
seed, 10,000 disposable warm-up iterations, and Python 3.10.12 reference:

| Runtime | Median training loop time per 50,000 iterations |
|---|---:|
| CPython 3.10.12 | 25.104 s |
| PyPy 7.3.19 | 5.473 s |
| Cython traversal prototype | 13.897 s |
| Rust release kernel | 0.413 s |

Those timings exclude setup and evaluation. The Rust kernel timing also excludes
Python/Rust state transfer and process launch; use the 881.35-second integrated
run above when estimating an actual long training job. All runtimes produced the
same training state for that fixed checkpoint and iteration count. Numba was
not used: its prototype segfaulted at 1,000 iterations.

## Running and resuming

The trainer accepts `--backend rust` for the external-sampling algorithm. Cargo
builds the release kernel locally on first use. Rust and Python use the same
checkpoint format, so either backend can resume a checkpoint created by the
other. Rust currently does not implement the historical `legacy` algorithm.

Example from a saved checkpoint:

```bash
python3 -m game_engine.training.benchmark \
  --backend rust \
  --resume artifacts/training-runs/rust-100m/external-42/checkpoint.pkl \
  --iterations 120000000 \
  --eval-every 1000000 \
  --output artifacts/training-runs/rust-120m
```

The 100-million run's checkpoint, policy, summary, and per-million metrics are
in the experiment output directory under the Codex workspace; they are kept out
of Git because checkpoints are generated model artifacts.
