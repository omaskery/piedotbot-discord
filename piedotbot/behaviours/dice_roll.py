from collections import namedtuple
import random
import re

from . import base_behaviour


RollDescription = namedtuple("RollDescription", "dice sides addition")
RollResult = namedtuple("RollResult", "rolls total average addition")


class Behaviour(base_behaviour.Behaviour):

    def __init__(self):
        super().__init__()
        self.allowed_channels = ["bot-shennanigans"]

    async def on_command(self, client, original_msg, relevant_content):
        max_rolls = 40

        author = original_msg.author

        roll = self.parse_command(relevant_content)

        if roll is None:
            return

        if roll.dice > max_rolls:
            await client.bot.send_message(original_msg.channel, f'{author.mention} no')
            return

        result = self.perform_rolls(roll)

        def with_addition(value):
            result_str = str(value)
            if result.addition is not None:
                result_str += f" (with {result.addition:+}: {value + result.addition})"
            return result_str

        msg = f'{author.mention} rolled {result.rolls}'
        if len(result.rolls) > 1:
             msg += f' for a total of {with_addition(result.total)}'

        # its very important to celebrate rolling a single nat 20
        if roll.sides == 20 and result.rolls == [20]:
            msg += f' - nat 20! :tada: :tada: :tada:'

        await client.bot.send_message(original_msg.channel, msg)

    @staticmethod
    def perform_rolls(roll: RollDescription):
        rolls = [random.randint(1, roll.sides) for _ in range(roll.dice)]
        total = sum(rolls)
        average = total / roll.dice
        return RollResult(rolls, total, average, roll.addition)

    @staticmethod
    def parse_command(relevant_content):
        words = relevant_content.split()
        if len(words) != 2 or words[0].lower() != 'roll':
            return None

        pattern = re.compile(r'(\d+)d(\d+)([+-]\d+)?')
        match = pattern.fullmatch(words[1])
        if match is None:
            return None

        dice, sides = int(match.group(1)), int(match.group(2))
        addition = int(match.group(3)) if match.group(3) is not None else None

        return RollDescription(dice, sides, addition)
