# Action-resolution curriculum on a larger Leduc game

The compiled research game now supports stacks through 14 chips and a chosen,
sorted menu of legal bet sizes. The full 14-chip menu has 13 bet sizes (`2` to
`14`), 74,624 public nodes, 230,397 information sets, and 648,789 action
entries. This is still the project's two-street, six-card modified Leduc game,
not Texas Hold'em. Exact best-response evaluation remains practical at this
size (about 1.4 seconds per full-game observation here).

The curriculum only needs to lift strategies **from coarse to fine**. Because
the fine menu contains every coarse bet size, every legal coarse history is
also present in the fine game. The fine game adds histories that use newly
introduced bet sizes; those have no learned coarse policy row and need an
initial policy before further fine-game training. They can start from a parent
or similar state's policy, or from a neutral policy such as uniform. A reverse
mapping from every fine history to an exact coarse history is not a requirement.

`game_engine.training.action_curriculum` lifts an average strategy from a
smaller betting menu to a larger one. It matches the **kind** of action first:
check, fold, call, or raise. Within the same kind, it maps a finer bet to the
nearest coarse size and **partitions** that coarse action's probability among
the finer bets in its bucket. The all-in bet maps to all-in where both states
allow it. Thus a parent bet with probability `0.6` split into three children
assigns `0.2` to each, not `0.6` to every child. If a coarse raise has no
directly assigned fine child, its mass moves to the nearest legal fine raise.
For this experiment, fine histories without a matching coarse decision start
uniform. The reported coverage is just the share of fine information sets that
receive a nonuniform warm start from the current history translator. It
measures this initialization rule, not whether the coarse game embeds in the
fine game. DCFR starts with the lifted policy as a finite prior in its
average-strategy table; new regret rows are small positive numbers
proportional to that policy, never copies of coarse regrets.

The current translator tries to reuse a coarse row for fine histories by
rounding each fine action back to a coarse action of the same kind. For example,
with six chips and coarse bets `{3, 6}`, the fine sequence
`check → bet 2 → raise to 3` cannot be translated as
`check → bet 3 → action 3`, because action 3 is a **call** in that coarse
state. The translator instead maps the raise to a coarse raise to 6. If that
coarse line then runs out of chips earlier than the fine line, later fine rows
receive the neutral initialization. This is one choice for seeding new rows;
another parent-state or feature-based warm start could seed them differently.

## Equal-time experiment

Each method received a 45-second wall-clock budget on one pinned CPU. The
clock includes solver creation, policy transfer, training, and exact
full-resolution evaluation. Shared Rust compilation and game-tree construction
were done before the clocks. The reported metric is exploitability in the
**13-size game**, in ante units (one ante equals one big blind here); lower is
better. Each curriculum spent 100 iterations at each earlier resolution, then
used its remaining time in the full game. The exact full-game evaluation ran
after each expansion and at roughly 10-second intervals thereafter. The direct
run used periodic full-game observations and a 45-second budget. The following
figures use the corrected, role-preserving transfer.

| Training path (bet sizes per stage) | Full-game exploitability on entry | Full-game iterations | Final full-game exploitability |
| --- | ---: | ---: | ---: |
| Direct: all 13 | 4.71932 (uniform) | 482 | 0.00509 |
| Broad: `2,7,14` → `2,4,7,10,14` → all 13 | 1.15315 | 431 | 0.00637 |
| Dense: seven even sizes → ten sizes → all 13 | 0.46134 | 412 | 0.00616 |

The broad and dense runs gave nonuniform warm starts to 22.5% and 69.1% of
fine-game information sets, respectively. These are unweighted counts, not
policy-reach mass. In the dense run, the remaining 30.9% are rows for which
this translator had no exact coarse decision to reuse: 8.1% first diverge
because a fine state offers an action kind (usually a raise) absent from its
translated coarse state; 19.9% are later rows below those branches; and 2.9%
have a forced coarse action while the fine game still offers choices. For
example, after `bet 7 → raise to 13`, the nearest legal coarse raise can be
all-in at 14, so later fine decisions differ. Those rows are new fine-game
states and uniform is simply the initialization tested here. The dense run's
lower entry exploitability did not carry through to a win over direct DCFR by
45 seconds.

An earlier numeric-only mapper wrongly conflated calls and raises of the same
size. Its results (`action-curriculum-14-v1`, `-short-broad`, `-dense`, and
`-short-narrow`) are retained as diagnostics, not as evidence for the corrected
curriculum. The all-in-only narrow first stage was also too severe to represent
ordinary bet-and-raise histories and was not rerun after the mapping fix.
An intermediate role-preserving run (`action-curriculum-14-role-preserving`)
did not yet redirect unmatched coarse raise mass to a fine raise; its results
are likewise superseded by the table above.

## Five-size start versus a middle stage

To keep stack depth fixed while starting with a broader action menu, I also
compared a five-size menu directly to the full game against the same five-size
menu with one nine-size stage in between. Both menus included the all-in. Each
run used a 45-second budget, 100 DCFR iterations in each coarse stage, and
exact full-game exploitability throughout.

| Path | Full-game exploitability on entry | Full-game iterations | Final full-game exploitability |
| --- | ---: | ---: | ---: |
| Direct: all 13 sizes | 4.71932 | 389 | **0.00790** |
| Five `{2,5,8,11,14}` → all 13 | 1.05636 | 286 | 0.01255 |
| Five → nine `{2,3,5,6,8,9,11,12,14}` → all 13 | 0.62512 | 290 | 0.01194 |

The intermediate stage improved slightly on the one-step curriculum, but both
were behind direct training in this run. The five-size prior supplied a
nonuniform start to 25.4% of final-game information sets; the nine-size prior
supplied one to 49.0%. These coverage counts describe the current initializer.
They are not a requirement for a curriculum: every old state remains in the
expanded game, and the other states are new rows that the chosen initializer
currently starts uniformly. These are single trials, so the small difference
between the two curricula is not conclusive.

Reproduce this comparison with:

```bash
python3 -m game_engine.training.experiment_curriculum \
  --chips 14 --seconds 45 --eval-every 10 \
  --coarse-iterations 100 --medium-iterations 100 \
  --methods direct five five_nine --cpu 0 \
  --output /tmp/action-curriculum-five
```

These are deterministic training runs but single wall-clock trials, so close
timings may vary by host load. The tested transfer does **not yet** demonstrate
a reliable speedup at this size. It also does not rule out action abstraction for Hold'em:
a larger game could give early low-resolution training more value, and a better
history translation could avoid many uniform fallbacks. The next focused test
would replace that fallback with a legal-state-aware projection, then compare
against direct DCFR at a larger time budget using the same full-game metric.

Reproduce the principal comparison with:

```bash
python3 -m game_engine.training.experiment_curriculum \
  --chips 14 --seconds 45 --eval-every 10 \
  --coarse-iterations 100 --medium-iterations 100 \
  --methods direct broad dense --cpu 0 \
  --output /tmp/action-curriculum-14
```

The output contains `metrics.jsonl`, `summary.json`, and a final `policy.pkl`
for each method. The recorded runs are in the task's
`outputs/optimization-sweep/action-curriculum-14-*` directories.

## Fixed-iteration convergence check

To check whether direct training was still improving beyond the short
wall-clock comparisons, I ran full-game DCFR to fixed iteration counts and
evaluated each checkpoint with the exact 14-chip best response. Compilation,
tree construction, and solver setup are outside the elapsed times; each time
includes training up to that checkpoint and its exact evaluation.

| Iterations | Elapsed | Exact exploitability (BB/hand) |
| ---: | ---: | ---: |
| 100 | 8.70 s | 0.07217 |
| 250 | 20.38 s | 0.01680 |
| 500 | 38.56 s | 0.00458 |
| 1,000 | 73.19 s | **0.00121** |

This is close to equilibrium for this small, finite game, though not an exact
solution. At 1,000 iterations the measured exploitability is about 0.12 BB per
100 hands. The curve was still falling at the last checkpoint, so these
measurements do not locate its final floor. The metrics are saved at
`outputs/verification/direct-dcfr-14-fixed-iterations/metrics.json`.

## Five-size start with an eight-size middle stage

The requested two-path comparison used the same five-size menu
`{2,5,8,11,14}` and either expanded straight to all 13 sizes or added the
eight-size menu `{2,3,5,7,8,11,12,14}` first. Each path had the same 45-second
budget, with 100 iterations at each coarse stage.

| Path | Final full-game exploitability | Fine-game iterations |
| --- | ---: | ---: |
| Five → all 13 | 0.00849 | 334 |
| Five → eight → all 13 | **0.00645** | 348 |

In this paired run, the extra stage improved the final score despite leaving
less time for full-game training. A prior direct 14-size run ended at 0.00790,
so the five-to-eight path is promising, though direct was not rerun alongside
this pair and each result is a single wall-clock trial. Reproduce the pair with:

```bash
python3 -m game_engine.training.experiment_curriculum \
  --chips 14 --seconds 45 --eval-every 10 \
  --coarse-iterations 100 --medium-iterations 100 \
  --methods five five_eight --cpu 0 \
  --output /tmp/action-curriculum-five-eight
```
