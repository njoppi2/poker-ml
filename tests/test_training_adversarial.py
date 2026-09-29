import json
import math
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from game_engine.training.evaluate import evaluate, expected_value
from game_engine.training.experimental_adversarial import (
    HeuristicLeague,
    CFRBestResponse,
    NativeCFRBestResponse,
    NativeBatchedSingleExploiter,
    NativeCounterExploiterBatch,
    NativeCoTrainingSingleExploiter,
    NativeHeuristicLeague,
    NativeTabularED,
    TabularED,
    best_response,
    counterfactual_action_values,
    joint_policy,
    main,
    project_simplex,
    run,
)
from game_engine.training.game import LeducGame


class ExactBestResponseTests(unittest.TestCase):
    def test_exposed_best_response_policy_has_evaluator_value_in_both_seats(self):
        game = LeducGame(2)
        policy = game.uniform_policy()
        for responder, scalar_key in ((0, "best_response_p0"), (1, "best_response_p1")):
            detail = best_response(game, policy, responder)
            deployed = joint_policy(game, detail["policy"], policy) if responder == 0 else \
                joint_policy(game, policy, detail["policy"])
            value = expected_value(game, deployed)
            response_value = value if responder == 0 else -value
            self.assertAlmostEqual(detail["value"], response_value, places=12)
            self.assertAlmostEqual(detail["value"], evaluate(game, policy)[scalar_key], places=12)
            for index, info in enumerate(game.infosets):
                if info.player == responder:
                    self.assertEqual(sum(detail["policy"][index]), 1.0)
                    self.assertIn(1.0, detail["policy"][index])
                    self.assertIsNotNone(detail["action_values"][index])

    def test_counterfactual_values_are_only_present_at_requested_players_infosets(self):
        game = LeducGame(2)
        rows = counterfactual_action_values(game, game.uniform_policy(), 0)
        for row, info in zip(rows, game.infosets):
            self.assertIsNone(row) if info.player == 1 else self.assertEqual(len(row), len(info.actions))

    def test_simplex_projection(self):
        self.assertEqual(project_simplex([2.0, -1.0]), [1.0, 0.0])
        row = project_simplex([0.2, 0.7, 1.3])
        self.assertAlmostEqual(sum(row), 1.0)
        self.assertTrue(all(value >= 0 for value in row))


class AdversarialTrainingTests(unittest.TestCase):
    def test_ed_updates_both_seats_and_reduces_a_short_exact_run(self):
        game = LeducGame(2)
        initial = evaluate(game, game.uniform_policy())["exploitability"]
        trainer = TabularED(game, step_size=0.25)
        before = [list(row) for row in trainer.policy]
        trainer.iteration()
        self.assertTrue(any(before[i] != trainer.policy[i]
                            for i, info in enumerate(game.infosets) if info.player == 0))
        self.assertTrue(any(before[i] != trainer.policy[i]
                            for i, info in enumerate(game.infosets) if info.player == 1))
        for _ in range(199):
            trainer.iteration()
        self.assertLess(evaluate(game, trainer.policy)["exploitability"], initial)

    def test_warm_start_is_deployed_before_training_and_common_advance_api_works(self):
        game = LeducGame(2)
        warm = game.uniform_policy()
        warm[0] = [1.0, 0.0]
        for trainer in (TabularED(game, initial_policy=warm),
                        HeuristicLeague(game, initial_policy=warm, refresh_every=3)):
            self.assertEqual(trainer.average_policy(), warm)
            trainer.advance(2)
            self.assertEqual(trainer.iterations, 2)
            self.assertEqual(len(trainer.current_policy()), len(game.infosets))

    def test_league_retains_bounded_fresh_exploiter_pairs_and_keeps_valid_policy(self):
        game = LeducGame(2)
        trainer = HeuristicLeague(game, step_size=0.1, refresh_every=2, max_snapshots=2)
        for _ in range(7):
            trainer.iteration()
        self.assertEqual(len(trainer.snapshots), 2)
        self.assertEqual(trainer.iterations, 7)
        self.assertGreaterEqual(evaluate(game, trainer.policy)["exploitability"], 0.0)

    def test_league_selects_one_complete_opponent_instead_of_rowwise_mixing(self):
        game = LeducGame(2)
        first = game.uniform_policy()
        second = game.uniform_policy()
        for index, info in enumerate(game.infosets):
            first[index] = [1.0] + [0.0] * (len(info.actions) - 1)
            second[index] = [0.0] * (len(info.actions) - 1) + [1.0]
        trainer = HeuristicLeague(game, self_play_weight=0.5)
        trainer.snapshots = [(first, second)]
        chosen = trainer._opponent_for_update(1)
        self.assertEqual(chosen, second)
        self.assertTrue(all(row in (base, snapshot)
                            for row, base, snapshot in zip(chosen, trainer.policy, second)))

    def test_budgeted_cli_writes_exact_deployed_evaluation(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "adversarial"
            main(["--algorithm", "league", "--chips", "2", "--iterations", "5",
                  "--refresh-every", "2", "--eval-every", "2", "--output", str(output)])
            summary = json.loads((output / "summary.json").read_text())
            metrics = [json.loads(line) for line in (output / "metrics.jsonl").read_text().splitlines()]
            self.assertEqual(summary["iteration"], 5)
            self.assertIn("exploitability", summary)
            self.assertEqual(metrics[0]["iteration"], 0)

    def test_time_budget_returns_a_valid_policy(self):
        policy, metrics = run("ed", chips=2, iterations=100_000, time_budget_s=0.001, eval_every=100)
        self.assertGreaterEqual(metrics[-1]["iteration"], 0)
        self.assertEqual(len(policy), len(LeducGame(2).infosets))

    def test_cfr_best_response_has_valid_own_reach_averaging_and_improves(self):
        game = LeducGame(2)
        initial = evaluate(game, game.uniform_policy())["exploitability"]
        trainer = CFRBestResponse(game)
        trainer.advance(200)
        averaged = trainer.average_policy()
        self.assertLess(evaluate(game, averaged)["exploitability"], initial)
        self.assertTrue(all(abs(sum(row) - 1.0) < 1e-12 for row in averaged))


@unittest.skipUnless(shutil.which("cargo"), "Rust toolchain is not installed")
class NativeParityTests(unittest.TestCase):
    def test_counter_exploiter_batch_resets_to_original_policy(self):
        game = LeducGame(2)
        rng = random.Random(91)
        warm = []
        for info in game.infosets:
            weights = [rng.random() for _ in info.actions]
            warm.append([weight / sum(weights) for weight in weights])

        def projected(policy, q0, q1, alpha):
            return [project_simplex(value + alpha * score
                    for value, score in zip(row, (q0 if info.player == 0 else q1)[index]))
                    for index, (row, info) in enumerate(zip(policy, game.infosets))]

        policy = [list(row) for row in warm]
        native = NativeCounterExploiterBatch(game, step_size=0.02, initial_policy=warm,
                                             responses=3, self_play_weight=0.25,
                                             response_growth=2.0)
        try:
            for iteration in range(3):
                alpha = 0.02 / math.sqrt(iteration + 1)
                probe = [list(row) for row in policy]
                responses = []
                for look in range(3):
                    response0 = best_response(game, probe, 0)["policy"]
                    response1 = best_response(game, probe, 1)["policy"]
                    responses.append((response0, response1))
                    if look < 2:
                        probe0 = counterfactual_action_values(game, joint_policy(game, probe, response1), 0)
                        probe1 = counterfactual_action_values(game, joint_policy(game, response0, probe), 1)
                        probe = projected(probe, probe0, probe1, alpha)
                self0 = counterfactual_action_values(game, policy, 0)
                self1 = counterfactual_action_values(game, policy, 1)
                batches = [[], []]
                for response0, response1 in responses:
                    batches[0].append(counterfactual_action_values(game, joint_policy(game, policy, response1), 0))
                    batches[1].append(counterfactual_action_values(game, joint_policy(game, response0, policy), 1))
                updated = []
                for index, (row, info) in enumerate(zip(policy, game.infosets)):
                    who = info.player
                    own = (self0 if who == 0 else self1)[index]
                    mixed = [0.75 * sum(weight * batch[index][action]
                                       for weight, batch in zip((1, 2, 4), batches[who])) / 7 +
                             0.25 * own[action] for action in range(len(row))]
                    updated.append(project_simplex(value + alpha * score
                                                   for value, score in zip(row, mixed)))
                policy = updated
            native.advance(1)
            native.advance(2)
            for expected, actual in zip(policy, native.average_policy()):
                for left, right in zip(expected, actual):
                    self.assertAlmostEqual(left, right, places=11)
        finally:
            native.close()

    def test_one_counter_exploiter_matches_exact_ed(self):
        game = LeducGame(2)
        ed = NativeTabularED(game, step_size=0.02)
        batch = NativeCounterExploiterBatch(game, step_size=0.02, responses=1)
        try:
            ed.advance(5)
            batch.advance(2)
            batch.advance(3)
            for expected, actual in zip(ed.average_policy(), batch.average_policy()):
                for left, right in zip(expected, actual):
                    self.assertAlmostEqual(left, right, places=12)
        finally:
            ed.close()
            batch.close()

    def test_co_training_updates_target_and_exploiter_from_same_prior_state(self):
        game = LeducGame(2)
        policy = game.uniform_policy()
        adversary0 = best_response(game, policy, 0)["policy"]
        adversary1 = best_response(game, policy, 1)["policy"]
        native = NativeCoTrainingSingleExploiter(game, step_size=0.2, refresh_every=100,
                                                  self_play_weight=0.25,
                                                  exploiter_step_multiplier=3.0)
        try:
            for iteration in range(5):
                q0_foe = counterfactual_action_values(game, joint_policy(game, policy, adversary1), 0)
                q1_foe = counterfactual_action_values(game, joint_policy(game, adversary0, policy), 1)
                q0_self = counterfactual_action_values(game, policy, 0)
                q1_self = counterfactual_action_values(game, policy, 1)
                q0_adversary = counterfactual_action_values(game, joint_policy(game, adversary0, policy), 0)
                q1_adversary = counterfactual_action_values(game, joint_policy(game, policy, adversary1), 1)
                alpha = 0.2 / math.sqrt(iteration + 1)
                updated_policy = []
                for index, info in enumerate(game.infosets):
                    foe = (q0_foe if info.player == 0 else q1_foe)[index]
                    own = (q0_self if info.player == 0 else q1_self)[index]
                    updated_policy.append(project_simplex(
                        value + alpha * (0.75 * opposing + 0.25 * own_value)
                        for value, opposing, own_value in zip(policy[index], foe, own)))
                    adversary = adversary0 if info.player == 0 else adversary1
                    scores = (q0_adversary if info.player == 0 else q1_adversary)[index]
                    adversary[index] = project_simplex(
                        value + 3.0 * alpha * score
                        for value, score in zip(adversary[index], scores))
                policy = updated_policy
            native.advance(2)
            native.advance(3)
            for expected_rows, actual_rows in ((policy, native.average_policy()),
                                               (adversary0, native.snapshots[0][0]),
                                               (adversary1, native.snapshots[0][1])):
                for expected, actual in zip(expected_rows, actual_rows):
                    for left, right in zip(expected, actual):
                        self.assertAlmostEqual(left, right, places=12)
        finally:
            native.close()

    def test_batched_exploiter_matches_separate_python_opponent_scores(self):
        game = LeducGame(2)
        policy = game.uniform_policy()
        native = NativeBatchedSingleExploiter(game, step_size=0.2, refresh_every=3,
                                               self_play_weight=0.25)
        try:
            for iteration in range(6):
                if iteration % 3 == 0:
                    exploiter0 = best_response(game, policy, 0)["policy"]
                    exploiter1 = best_response(game, policy, 1)["policy"]
                against0 = counterfactual_action_values(game, joint_policy(game, policy, exploiter1), 0)
                against1 = counterfactual_action_values(game, joint_policy(game, exploiter0, policy), 1)
                self0 = counterfactual_action_values(game, policy, 0)
                self1 = counterfactual_action_values(game, policy, 1)
                alpha = 0.2 / math.sqrt(iteration + 1)
                updated = []
                for index, info in enumerate(game.infosets):
                    opponent_scores = (against0 if info.player == 0 else against1)[index]
                    own_scores = (self0 if info.player == 0 else self1)[index]
                    updated.append(project_simplex(
                        value + alpha * (0.75 * foe + 0.25 * own)
                        for value, foe, own in zip(policy[index], opponent_scores, own_scores)))
                policy = updated
            native.advance(2)
            native.advance(4)
            for expected, actual in zip(policy, native.average_policy()):
                for left, right in zip(expected, actual):
                    self.assertAlmostEqual(left, right, places=12)
        finally:
            native.close()

    def test_single_fresh_exploiter_matches_exact_ed(self):
        """Refreshing the sole exploiter every update is the ED control."""
        game = LeducGame(2)
        ed = NativeTabularED(game, step_size=0.1)
        single = NativeHeuristicLeague(game, step_size=0.1, refresh_every=1,
                                        max_snapshots=1, self_play_weight=0.0)
        try:
            ed.advance(6)
            single.advance(2)
            single.advance(4)
            for ed_row, single_row in zip(ed.average_policy(), single.average_policy()):
                for expected, actual in zip(ed_row, single_row):
                    self.assertAlmostEqual(expected, actual, places=12)
        finally:
            ed.close()
            single.close()

    def test_native_cfr_br_is_batch_boundary_invariant_and_improves(self):
        game = LeducGame(2)
        initial = evaluate(game, game.uniform_policy())["exploitability"]
        continuous, split = NativeCFRBestResponse(game), NativeCFRBestResponse(game)
        try:
            continuous.advance(200)
            split.advance(73)
            split.advance(127)
            self.assertEqual(continuous.iterations, split.iterations)
            for expected, actual in zip(continuous.current_policy(), split.current_policy()):
                for left, right in zip(expected, actual):
                    self.assertAlmostEqual(left, right, places=14)
            for expected, actual in zip(continuous.average_policy(), split.average_policy()):
                for left, right in zip(expected, actual):
                    self.assertAlmostEqual(left, right, places=14)
            self.assertLess(evaluate(game, continuous.average_policy())["exploitability"], initial)
        finally:
            continuous.close()
            split.close()

    @unittest.skipIf(sys.version_info >= (3, 12),
                     "strict Rust/Python sum parity requires the pre-3.12 sum implementation")
    def test_native_cfr_br_matches_python_state_on_compatible_python(self):
        for chips in (2, 4):
            game = LeducGame(chips)
            python, native = CFRBestResponse(game), NativeCFRBestResponse(game)
            try:
                python.advance(5)
                native.advance(2)
                native.advance(3)
                for expected_rows, actual_rows in ((python.regrets, native.regrets),
                                                   (python.strategy_sums, native.strategy_sums),
                                                   (python.current_policy(), native.current_policy()),
                                                   (python.average_policy(), native.average_policy())):
                    for expected, actual in zip(expected_rows, actual_rows):
                        for left, right in zip(expected, actual):
                            self.assertAlmostEqual(left, right, places=12)
            finally:
                native.close()

    def test_native_ed_and_whole_opponent_league_match_python_for_random_warm_starts(self):
        rng = random.Random(91)
        cases = ((TabularED, NativeTabularED, {}),
                 (HeuristicLeague, NativeHeuristicLeague,
                  {"refresh_every": 2, "max_snapshots": 3, "self_play_weight": 0.5}))
        for chips in (2, 4):
            game = LeducGame(chips)
            warm = []
            for info in game.infosets:
                weights = [rng.random() for _ in info.actions]
                warm.append([weight / sum(weights) for weight in weights])
            for python_cls, native_cls, kwargs in cases:
                with self.subTest(chips=chips, algorithm=python_cls.__name__):
                    python = python_cls(game, step_size=0.2, initial_policy=warm, **kwargs)
                    native = native_cls(game, step_size=0.2, initial_policy=warm, **kwargs)
                    try:
                        python.advance(5)
                        native.advance(2)
                        native.advance(3)
                        self.assertEqual(native.iterations, python.iterations)
                        for expected, actual in zip(python.average_policy(), native.average_policy()):
                            for left, right in zip(expected, actual):
                                self.assertAlmostEqual(left, right, places=12)
                        self.assertEqual(len(native.snapshots), len(getattr(python, "snapshots", ())))
                    finally:
                        native.close()


if __name__ == "__main__":
    unittest.main()
