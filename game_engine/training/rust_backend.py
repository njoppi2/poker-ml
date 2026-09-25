"""Rust-accelerated backend for the external-sampling Leduc trainer."""
from array import array
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from .solver import ExternalSampling


CRATE = Path(__file__).with_name("rust_kernel")
BINARY = CRATE / "target" / "release" / "leduc-kernel"
_BUILT = False


def build_kernel():
    global _BUILT
    if _BUILT and BINARY.exists():
        return BINARY
    cargo = shutil.which("cargo")
    if not cargo:
        raise RuntimeError("Rust backend requires cargo; install the Rust toolchain")
    subprocess.run([cargo, "build", "--release", "--manifest-path", str(CRATE / "Cargo.toml")], check=True)
    if not BINARY.exists():
        raise RuntimeError("cargo completed but the Leduc Rust kernel was not created")
    _BUILT = True
    return BINARY


def _little_endian_array(typecode, values):
    result = array(typecode, values)
    if sys.byteorder != "little":
        result.byteswap()
    return result.tobytes()


class RustExternalSampling(ExternalSampling):
    """ExternalSampling state/API whose iteration batches execute in Rust."""

    name = "external"

    def __init__(self, game, seed=42, state=None):
        super().__init__(game, seed)
        self.binary = build_kernel()
        self._scratch = tempfile.TemporaryDirectory(prefix="leduc-rust-")
        self._input = Path(self._scratch.name) / "input.bin"
        self._output = Path(self._scratch.name) / "output.bin"
        if state is not None:
            if state.get("algorithm") != "external" or state.get("chips") != game.chips:
                raise ValueError("Rust backend can resume only a matching external-sampling checkpoint")
            self.iterations = state["iterations"]
            self.rng.setstate(state["rng_state"])
            self.regrets = state["regrets"]
            self.strategy_sums = state["strategy_sums"]
            self.visited = state["visited"]
            self.node_visits = state["node_visits"]

    def advance(self, iterations):
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
            raise ValueError("iterations must be a nonnegative integer")
        if iterations == 0:
            return
        self._write_input(iterations)
        subprocess.run([str(self.binary), str(self._input), str(self._output)], check=True,
                       stdout=subprocess.DEVNULL)
        self._read_output()

    def _write_input(self, iterations):
        game = self.game
        children, child_offsets = [], [0]
        for node in game.nodes:
            children.extend(node.children)
            child_offsets.append(len(children))
        action_offsets = [0]
        for info in game.infosets:
            action_offsets.append(action_offsets[-1] + len(info.actions))
        flat_regrets = [x for row in self.regrets for x in row]
        flat_sums = [x for row in self.strategy_sums for x in row]
        if len(flat_regrets) != action_offsets[-1] or len(flat_sums) != action_offsets[-1]:
            raise ValueError("checkpoint strategy arrays do not match the compiled game")
        state = self.rng.getstate()
        if state[0] != 3 or state[2] is not None or len(state[1]) != 625:
            raise ValueError("Rust backend currently requires Python MT19937 random state")
        deals = len(game.deals)
        data = bytearray(b"LDRUST01")
        data.extend(struct.pack("<8Q", iterations, len(game.nodes), deals, len(game.infosets),
                                len(children), len(flat_regrets), self.iterations, self.node_visits))
        data.extend(struct.pack("<624I", *state[1][:624]))
        data.extend(struct.pack("<I", state[1][624]))
        data.extend(_little_endian_array("b", (node.player for node in game.nodes)))
        data.extend(_little_endian_array("Q", child_offsets))
        data.extend(_little_endian_array("I", children))
        info_ids = (info_id for node in game.nodes
                    for info_id in (node.infos if node.infos else (0,) * deals))
        data.extend(_little_endian_array("I", info_ids))
        payoffs = (payoff for node in game.nodes
                   for payoff in (node.payoffs if node.payoffs else (0.0,) * deals))
        data.extend(_little_endian_array("d", payoffs))
        data.extend(_little_endian_array("d", game.chance))
        data.extend(_little_endian_array("Q", action_offsets))
        data.extend(_little_endian_array("d", flat_regrets))
        data.extend(_little_endian_array("d", flat_sums))
        visited = bytearray(len(game.infosets))
        for info_id in self.visited:
            visited[info_id] = 1
        data.extend(visited)
        self._input.write_bytes(data)

    def _read_output(self):
        data = memoryview(self._output.read_bytes())
        offset = 0

        def take(size):
            nonlocal offset
            chunk = data[offset:offset + size]
            if len(chunk) != size:
                raise ValueError("truncated Rust solver output")
            offset += size
            return chunk

        if bytes(take(8)) != b"LDRSOUT1":
            raise ValueError("invalid Rust solver output header")
        self.iterations, self.node_visits = struct.unpack("<QQ", take(16))
        elapsed_bits = struct.unpack("<Q", take(8))[0]
        self._last_kernel_seconds = struct.unpack("<d", struct.pack("<Q", elapsed_bits))[0]
        mt_index = struct.unpack("<I", take(4))[0]
        mt = struct.unpack("<624I", take(624 * 4))
        self.rng.setstate((3, tuple(mt) + (mt_index,), None))
        n_actions = sum(len(info.actions) for info in self.game.infosets)
        flat_regrets = struct.unpack(f"<{n_actions}d", take(n_actions * 8))
        flat_sums = struct.unpack(f"<{n_actions}d", take(n_actions * 8))
        visited = take(len(self.game.infosets))
        if offset != len(data):
            raise ValueError("unexpected trailing bytes in Rust solver output")
        self.regrets, self.strategy_sums = [], []
        pos = 0
        for info in self.game.infosets:
            end = pos + len(info.actions)
            self.regrets.append(list(flat_regrets[pos:end]))
            self.strategy_sums.append(list(flat_sums[pos:end]))
            pos = end
        self.visited = {i for i, flag in enumerate(visited) if flag}

    def close(self):
        self._scratch.cleanup()
