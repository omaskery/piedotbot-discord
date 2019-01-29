from piedotbot.behaviours.dice_roll import RollDescription, RollCommand, RollResult, Behaviour
import unittest


class TestDiceRolling(unittest.TestCase):

    def test_rolling(self):
        for dice_count in [4, 8, 20]:
            for dice_sides in [2, 3, 5, 6, 10, 20]:
                with self.subTest("specific dice count and side count", dice_count=dice_count, dice_sides=dice_sides):
                    roll_info = RollDescription(dice=dice_count, sides=dice_sides)

                    result = Behaviour.perform_roll(roll_info)

                    self.assertEqual(dice_count, len(result), "got wrong number of dice rolls back")
                    self.assertTrue(all((
                        1 <= value <= dice_sides
                        for value in result
                    )), "some dice had impossible values")

    def test_roll_specifier_parsing(self):
        cases = [
            ("roll 1d4", RollCommand([RollDescription(1, 4)], None)),
            ("roll 2d10", RollCommand([RollDescription(2, 10)], None)),
            ("roll 16d3", RollCommand([RollDescription(16, 3)], None)),
            ("ROLL 16d3", RollCommand([RollDescription(16, 3)], None)),  # should be case insensitive
            ("roll 2d20+8", RollCommand([RollDescription(2, 20)], 8)),
            ("roll 2d20-8", RollCommand([RollDescription(2, 20)], -8)),
            ("roll 16d3+20", RollCommand([RollDescription(16, 3)], 20)),
            ("roll", None),  # must have a specifier
            ("rull 16d3", None),  # first word must be "roll"
            ("", None),  # must have 2 words
            ("r", None),  # must have 2 words
            ("roll 2d10 butts", None),  # must have 2 words
        ]

        for stimulus, expected in cases:
            with self.subTest("specific case", stimulus=stimulus, expected=expected):
                actual_result = Behaviour.parse_command(stimulus)
                self.assertEqual(expected, actual_result, "actual result did not match expected")

    def test_responses(self):
        cases = [
            (RollCommand([RollDescription(400, 4)], None), r"^400d4\? no$"),
            (RollCommand([RollDescription(0, 4)], None), r"^0d4\? don't be a knob$"),
            (RollCommand([RollDescription(4, 0)], None), r"^4d0\? honestly\? come on :/$"),
            (RollCommand([RollDescription(1, 4)], None), r"^rolled 1d4: [1-4]$"),
            (RollCommand([RollDescription(1, 8)], None), r"^rolled 1d8: [1-8]$"),
            (RollCommand([RollDescription(2, 4)], None), r"^rolled 2d4: \[[1-4], [1-4]\] for a total of \d+$"),
            (RollCommand([RollDescription(2, 8)], None), r"^rolled 2d8: \[[1-8], [1-8]\] for a total of \d+$"),
            (
                RollCommand([RollDescription(2, 8), RollDescription(3, 20)], None),
                r"^rolled 2d8: \[[1-8], [1-8]\] 3d20: \[\d+, \d+, \d+\] for a total of \d+$"
            ),
            (
                RollCommand([RollDescription(3, 6), RollDescription(2, 8)], 20),
                r"^rolled 3d6: \[\d+, \d+, \d+\] 2d8: \[\d+, \d+\] for a total of \d+ with a modifier of [+-]\d+: \d+$"
            ),
        ]

        for stimulus, expected in cases:
            with self.subTest("specific case", stimulus=stimulus, expected=expected):
                actual_result = Behaviour.generate_response(stimulus)
                self.assertRegex(actual_result, expected, "actual result did not match expected")
