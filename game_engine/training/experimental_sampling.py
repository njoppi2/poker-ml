"""Experimental weighted and baseline-corrected external-sampling MCCFR.

These alternatives are deliberately separate from the production checkpoint CLI.
Linear weighting multiplies this iteration's regret and strategy increments by
t; this is algebraically equivalent to discounting both tables by t/(t+1)
after each iteration (up to a common scale). VR uses a state/deal baseline:
at sampled opponent nodes, sum_a p(a)b(a) + v(sampled) - b(sampled).
It leaves chance sampling unchanged. Baselines are read before their recursive
updates, so the correction is unbiased conditional on past training history.
See Schmid et al., https://arxiv.org/abs/1809.03057.
"""
import subprocess
import tempfile
from pathlib import Path

from .rust_backend import RustExternalSampling
from .solver import ExternalSampling

CRATE = Path(__file__).with_name("sampled_variants_kernel")
BINARY = CRATE / "target/release/sampled-variants"
_BUILT = False


def build_kernel():
    global _BUILT
    if not _BUILT or not BINARY.exists():
        subprocess.run(["cargo", "build", "--release", "--manifest-path", str(CRATE / "Cargo.toml")], check=True)
        _BUILT = True
    return BINARY


class SampledVariant(RustExternalSampling):
    def __init__(self, game, seed=42, mode="linear", baseline_rate=0.5):
        if mode not in {"plain", "linear", "vr", "vr-linear"}:
            raise ValueError("invalid sampled variant")
        if not 0 <= baseline_rate <= 1:
            raise ValueError("baseline rate must be between zero and one")
        ExternalSampling.__init__(self, game, seed)
        self.mode = mode
        self.name = "sampled-" + mode
        self.baseline_rate = baseline_rate
        self.binary = build_kernel()
        self._scratch = tempfile.TemporaryDirectory(prefix="leduc-sampled-")
        self._input = Path(self._scratch.name) / "input.bin"
        self._output = Path(self._scratch.name) / "output.bin"
        self._baselines = Path(self._scratch.name) / "baselines.bin"

    def advance(self, iterations):
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
            raise ValueError("iterations must be a nonnegative integer")
        if not iterations:
            return
        self._write_input(iterations)
        subprocess.run([str(self.binary), str(self._input), str(self._output), self.mode,
                        str(self._baselines), str(self.baseline_rate)], check=True,
                       stdout=subprocess.DEVNULL)
        self._read_output()

    def state_dict(self):
        state = super().state_dict()
        state.update(mode=self.mode, baseline_rate=self.baseline_rate,
                     baselines=self._baselines.read_bytes() if self._baselines.exists() else None)
        return state
