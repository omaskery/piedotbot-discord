from piedotbot.behaviours import dice_roll
import unittest


class TestDiceRolling(unittest.TestCase):

    def test_rolling(self):
        for dice_count in [4, 8, 20]:
            for dice_sides in [2, 3, 5, 6, 10, 20]:
                with self.subTest("specific dice count and side count", dice_count=dice_count, dice_sides=dice_sides):
                    roll_info = dice_roll.RollDescription(dice=dice_count, sides=dice_sides, addition=None)

                    result = dice_roll.Behaviour.perform_rolls(roll_info)

                    self.assertEqual(dice_count, len(result.rolls), "got wrong number of dice rolls back")
                    self.assertTrue(all((
                        1 <= value <= dice_sides
                        for value in result.rolls
                    )), "some dice had impossible values")
                    self.assertEqual(sum(result.rolls), result.total, "total doesnt match expected value")

    def test_roll_specifier_parsing(self):
        cases = [
            ("roll 1d4", (1, 4, None)),
            ("roll 2d10", (2, 10, None)),
            ("roll 16d3", (16, 3, None)),
            ("ROLL 16d3", (16, 3, None)),  # should be case insensitive
            ("roll 2d20+8", (2, 20, 8)),
            ("roll 2d20-8", (2, 20, -8)),
            ("roll 16d3+20", (16, 3, 20)),
            ("roll", None),  # must have a specifier
            ("rull 16d3", None),  # first word must be "roll"
            ("", None),  # must have 2 words
            ("r", None),  # must have 2 words
            ("roll 2d10 butts", None),  # must have 2 words
        ]

        for case in cases:
            stimulus, expected = case
            with self.subTest("specific case", stimulus=stimulus, expected=expected):
                actual_result = dice_roll.Behaviour.parse_command(stimulus)
                self.assertEqual(expected, actual_result, "actual result did not match expected")
