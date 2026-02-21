import unittest

from game_engine.functions import reorder_list


class ReorderListTests(unittest.TestCase):
    def test_rotates_list_to_first_matching_element(self) -> None:
        values = [1, 2, 3, 4]
        rotated = reorder_list(values, lambda item: item == 3)
        self.assertEqual(rotated, [3, 4, 1, 2])

    def test_returns_original_when_no_match(self) -> None:
        values = ["a", "b", "c"]
        rotated = reorder_list(values, lambda item: item == "z")
        self.assertEqual(rotated, values)

    def test_works_with_dictionary_condition(self) -> None:
        values = [
            {"id": "p1", "score": 5},
            {"id": "p2", "score": 9},
            {"id": "p3", "score": 7},
        ]
        rotated = reorder_list(values, lambda item: item["score"] >= 8)
        self.assertEqual([item["id"] for item in rotated], ["p2", "p3", "p1"])


if __name__ == "__main__":
    unittest.main()
