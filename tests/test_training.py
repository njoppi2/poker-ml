import contextlib
import hashlib
import io
import json
import pickle
import random
import tempfile
import unittest
from pathlib import Path

from game_engine.training.benchmark import load_blueprint, load_checkpoint, main, save_checkpoint
from game_engine.training.evaluate import evaluate
from game_engine.training.game import LeducGame, showdown
from game_engine.training.solver import ExternalSampling, LegacySampling, restore


class GameTests(unittest.TestCase):
    def test_chance_counts_physical_cards_and_hides_the_opponent(self):
        game = LeducGame(4)
        self.assertEqual(len(game.deals), 24)
        self.assertAlmostEqual(sum(game.chance), 1)
        self.assertEqual(game.chance[game.deals.index((0, 0, 1))], 1 / 30)
        self.assertEqual(game.chance[game.deals.index((0, 1, 2))], 1 / 15)
        root = game.nodes[0]
        self.assertEqual(root.infos[game.deals.index((0, 1, 2))], root.infos[game.deals.index((0, 2, 1))])
        self.assertNotEqual(root.infos[game.deals.index((0, 1, 2))], root.infos[game.deals.index((1, 0, 2))])

    def test_showdown_pair_high_card_and_tie(self):
        self.assertEqual(showdown((0, 2, 0)), 1)
        self.assertEqual(showdown((2, 0, 1)), 1)
        self.assertEqual(showdown((0, 2, 2)), -1)
        self.assertEqual(showdown((1, 1, 0)), 0)

    def test_preflop_fold_returns_unmatched_bet(self):
        game = LeducGame(4)
        # P0 raises to 4, P1 folds. P0 nets only the opponent's ante.
        raise_node = game.nodes[game.nodes[0].children[-1]]
        terminal = game.nodes[raise_node.children[0]]
        self.assertEqual(terminal.payoffs, (1.0,) * 24)

    def test_compilation_actions_and_payoff_bounds(self):
        for chips in (2, 4, 12):
            game = LeducGame(chips)
            for index, node in enumerate(game.nodes):
                if node.player < 0:
                    self.assertTrue(all(abs(value) <= chips for value in node.payoffs))
                else:
                    self.assertTrue(all(child > index for child in node.children))
                    self.assertTrue(all(len(game.infosets[i].actions) == len(node.children) for i in node.infos))

    def test_invalid_size(self):
        for chips in (1, 13, 2.5, True):
            with self.assertRaises(ValueError):
                LeducGame(chips)


class EvaluationTests(unittest.TestCase):
    def test_uniform_policy_reference_values(self):
        # Independently verified against OpenSpiel's best-response evaluator.
        game = LeducGame(2)
        values = evaluate(game, game.uniform_policy())
        self.assertAlmostEqual(values['best_response_p0'], 0.5)
        self.assertAlmostEqual(values['best_response_p1'], 0.25)
        self.assertAlmostEqual(values['exploitability'], 0.375)

    def test_invalid_policy_is_rejected(self):
        game = LeducGame(2)
        for row in ([1.0], [-1.0, 2.0], [float('nan'), 0.0], [0.1, 0.1]):
            policy = game.uniform_policy()
            policy[0] = row
            with self.assertRaises(ValueError):
                evaluate(game, policy)

    def test_best_response_dominates_policy_value(self):
        game = LeducGame(4)
        rng = random.Random(13)
        rows = []
        for info in game.infosets:
            row = [rng.random() for _ in info.actions]
            rows.append([x / sum(row) for x in row])
        result = evaluate(game, rows)
        self.assertGreaterEqual(result['best_response_p0'], result['value_p0'])
        self.assertGreaterEqual(result['best_response_p1'], -result['value_p0'])

    def test_blueprint_fallback_and_action_validation(self):
        game = LeducGame(2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'policy.pkl'
            path.write_bytes(pickle.dumps({}))
            rows, missing = load_blueprint(game, path)
            self.assertEqual(missing, len(game.infosets))
            self.assertEqual(rows[game.info_by_key[':|A']], [1.0, 0.0])
            self.assertEqual(rows[game.info_by_key['r200:|A']], [0.0, 1.0])
            path.write_bytes(pickle.dumps({':|A': ([9, 10], [0.5, 0.5])}))
            with self.assertRaises(ValueError):
                load_blueprint(game, path)


class SolverTests(unittest.TestCase):
    def test_legacy_cleanup_preserves_original_update_fixtures(self):
        # Captured from the unmodified f0ca5bd trainer, 50 iterations, 4 chips.
        # Quantize only the fixture comparison: Python 3.12+ changed float sum.
        expected = {
            42: 'a6f6a35c1d174e78313f2df34fc7563c461a1844ab8f691930a69c0dd652a85a',
            43: '0ba23a2b1ae913b009c2115350c9e26e1905b4e85d67fabfa63eb1238e9f5aa6',
        }
        game = LeducGame(4)
        for seed, digest in expected.items():
            solver = LegacySampling(game, seed)
            for _ in range(50):
                solver.iteration()
            state = [(k, [round(v, 8) + 0.0 for v in n.regret_sum],
                      [round(v, 8) + 0.0 for v in n.strategy_sum])
                     for k, n in sorted(solver.trainer.node_history_map.items())]
            actual = hashlib.sha256(json.dumps(state, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(actual, digest)

    def test_external_sampling_improves_exact_exploitability(self):
        game = LeducGame(4)
        initial = evaluate(game, game.uniform_policy())['exploitability']
        solver = ExternalSampling(game, 42)
        for _ in range(2000):
            solver.iteration()
        self.assertLess(evaluate(game, solver.average_policy())['exploitability'], initial / 2)

    def test_checkpoint_resume_preserves_every_update(self):
        game = LeducGame(4)
        for solver_type in (ExternalSampling, LegacySampling):
            with self.subTest(solver=solver_type.name), tempfile.TemporaryDirectory() as folder:
                continuous = solver_type(game, 43)
                interrupted = solver_type(game, 43)
                for _ in range(30):
                    continuous.iteration()
                for _ in range(13):
                    interrupted.iteration()
                path = Path(folder) / 'checkpoint.pkl'
                save_checkpoint(path, interrupted, 43, 1.5)
                saved = load_checkpoint(path)
                resumed = restore(game, saved['state'])
                for _ in range(17):
                    resumed.iteration()
                self.assertEqual(continuous.average_policy(), resumed.average_policy())
                self.assertEqual(continuous.node_visits, resumed.node_visits)
                self.assertEqual(continuous.rng.getstate(), resumed.rng.getstate())
                if solver_type is ExternalSampling:
                    self.assertEqual(continuous.regrets, resumed.regrets)
                    self.assertEqual(continuous.strategy_sums, resumed.strategy_sums)
                else:
                    for key, node in continuous.trainer.node_history_map.items():
                        other = resumed.trainer.node_history_map[key]
                        self.assertEqual(node.regret_sum, other.regret_sum)
                        self.assertEqual(node.strategy_sum, other.strategy_sum)

    def test_seed_isolation(self):
        game = LeducGame(2)
        before = random.getstate()
        for cls in (ExternalSampling, LegacySampling):
            cls(game, 12).iteration()
            self.assertEqual(random.getstate(), before)

    def test_cli_stops_at_target_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            output = Path(folder) / 'run'
            args = ['--chips', '2', '--algorithms', 'external', '--target', '0.4', '--output', str(output)]
            main(args)
            summary = json.loads((output / 'summary.json').read_text())[0]
            self.assertEqual(summary['stop_reason'], 'target')
            self.assertEqual(summary['final']['iteration'], 0)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)

    def test_cli_resumes_to_requested_total(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            first, second = Path(folder) / 'first', Path(folder) / 'second'
            main(['--chips', '2', '--algorithms', 'external', '--iterations', '3', '--output', str(first)])
            main(['--resume', str(first / 'external-42' / 'checkpoint.pkl'), '--iterations', '7', '--output', str(second)])
            summary = json.loads((second / 'summary.json').read_text())[0]
            self.assertEqual(summary['initial_iteration'], 3)
            self.assertEqual(summary['final']['iteration'], 7)


if __name__ == '__main__':
    unittest.main()
