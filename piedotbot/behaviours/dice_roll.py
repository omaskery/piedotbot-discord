from collections import namedtuple
import random
import re

from . import base_behaviour


RollDescription = namedtuple("RollDescription", "dice sides")
RollResult = namedtuple("RollResult", "rolls total average")


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

        msg = f'{author.mention} rolled {result.rolls} for a total of {result.total} and average of {result.average}'
        await client.bot.send_message(original_msg.channel, msg)

    @staticmethod
    def perform_rolls(roll):
        rolls = [random.randint(1, roll.sides) for _ in range(roll.dice)]
        total = sum(rolls)
        average = total / roll.dice
        return RollResult(rolls, total, average)

    @staticmethod
    def parse_command(relevant_content):
        words = relevant_content.split()
        if len(words) != 2 or words[0].lower() != 'roll':
            return None

        pattern = re.compile(r'(\d+)d(\d+)')
        match = pattern.fullmatch(words[1])
        if match is None:
            return None

        dice, sides = int(match.group(1)), int(match.group(2))

        return RollDescription(dice, sides)
