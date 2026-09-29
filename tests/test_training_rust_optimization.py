"""Baseline state fixtures for the allocation-reduced Rust kernel."""
import hashlib
import shutil
import unittest

from game_engine.training.game import LeducGame


@unittest.skipUnless(shutil.which("cargo"), "Rust toolchain is not installed")
class RustOptimizationParityTests(unittest.TestCase):
    # SHA-256 of the complete native output excluding only elapsed-time bytes,
    # captured from baseline 821d862 at chips=12, seed=7319.
    BASELINE_DIGESTS = {
        42: {
            1: "43f0e2fd59180b564897500820acabf98bfa23ec70ee3ed9f285727790fcb509",
            7: "6ac8981c5292655ea9f4b11a0f7366b8855a0092e83d041de71992e3c0fabf71",
            13: "c6b58611cb566dd06a9e169d3f1e5c230a5c741b27765b9e788bfac35150f522",
        },
        7319: {
            1: "5a8f440bec4298968efccd0483010909f9b63f9733595e6ed7b42292e017c05d",
            7: "2736be84bd717fa2cd4e25c165d575c1b48e5f427cf76a75a0aabd081f07893b",
            13: "6446dcc26b300374f42a021436d8ce188e2ec8af4725f2b273f5bad310f53680",
        },
    }

    def test_maximum_action_game_matches_baseline_state(self):
        from game_engine.training.rust_backend import RustExternalSampling

        game = LeducGame(12)
        self.assertEqual(max(len(info.actions) for info in game.infosets), 12)
        for seed, runs in self.BASELINE_DIGESTS.items():
            for iterations, expected in runs.items():
                with self.subTest(seed=seed, iterations=iterations):
                    solver = RustExternalSampling(game, seed=seed)
                    try:
                        solver.advance(iterations)
                        raw = solver._output.read_bytes()
                        actual = hashlib.sha256(raw[:24] + raw[32:]).hexdigest()
                        self.assertEqual(actual, expected)
                    finally:
                        solver.close()

    def test_checkpoint_resume_matches_uninterrupted_native_run(self):
        from game_engine.training.rust_backend import RustExternalSampling

        game = LeducGame(12)
        direct = RustExternalSampling(game, seed=7319)
        segmented = RustExternalSampling(game, seed=7319)
        try:
            direct.advance(21)
            segmented.advance(7)
            saved = segmented.state_dict()
            segmented.close()
            segmented = RustExternalSampling(game, state=saved)
            segmented.advance(14)
            self.assertEqual(direct.state_dict(), segmented.state_dict())
        finally:
            direct.close()
            segmented.close()


if __name__ == "__main__":
    unittest.main()
