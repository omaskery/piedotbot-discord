from collections import namedtuple
import random
import re

from . import base_behaviour


RollDescription = namedtuple("RollDescription", "dice sides")


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

        total = 0
        rolls = []
        for index in range(roll.dice):
            roll_result = random.randint(1, roll.sides)
            if roll.dice <= max_rolls:
                rolls.append(roll_result)
            total += roll_result

        average = total / roll.dice
        msg = f'{author.mention} rolled {rolls} for a total of {total} and average of {average}'
        await client.bot.send_message(original_msg.channel, msg)

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
