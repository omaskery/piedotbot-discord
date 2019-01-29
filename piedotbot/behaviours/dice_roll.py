from dataclasses import dataclass
import typing
import random
import re

from . import base_behaviour


MAX_ROLLS = 40


@dataclass(frozen=True)
class RollDescription:
    dice: int
    sides: int

    def __str__(self):
        return f"{self.dice}d{self.sides}"


@dataclass(frozen=True)
class RollCommand:
    roll_descriptions: typing.List[RollDescription]
    addition: typing.Optional[int]


@dataclass(frozen=True)
class RollResult:
    rolls: typing.List[typing.Tuple[RollDescription, typing.List[int]]]
    total: int
    addition: typing.Optional[int]
    number_of_dice_rolled: int


class Behaviour(base_behaviour.Behaviour):

    def __init__(self):
        super().__init__()
        self.allowed_channels = ["bot-shennanigans"]

    async def on_command(self, client, original_msg, relevant_content):
        author = original_msg.author

        command = self.parse_command(relevant_content)

        if command is None:
            return

        response = self.generate_response(command)

        await client.bot.send_message(original_msg.channel, f'{author.mention} {response}')

    @staticmethod
    def generate_response(command: RollCommand) -> str:
        for roll in command.roll_descriptions:
            if roll.dice > MAX_ROLLS:
                return f'{roll}? no'
            elif roll.dice < 1:
                return f'{roll}? don\'t be a knob'
            elif roll.sides < 1:
                return f'{roll}? honestly? come on :/'

        result = Behaviour.run_command(command)

        msg = f'rolled'

        def show_single_result(description, rolls):
            return f' {description}: {rolls if len(rolls) > 1 else rolls[0]}'

        for description, rolls in result.rolls:
            msg += show_single_result(description, rolls)

        if result.number_of_dice_rolled > 1:
            msg += f' for a total of {result.total}'
        if result.addition is not None:
            msg += f' with a modifier of {result.addition:+}: {result.total + result.addition}'

        # its very important to celebrate rolling a single nat 20
        if result.number_of_dice_rolled == 1 and result.rolls[0][0].sides == 20 and result.rolls[0][1] == [20]:
            msg += f' - nat 20! :tada: :tada: :tada:'

        return msg

    @staticmethod
    def run_command(command: RollCommand) -> RollResult:
        rolls_by_dice = [
            (description, Behaviour.perform_roll(description))
            for description in command.roll_descriptions
        ]
        return RollResult(
            rolls=rolls_by_dice,
            total=sum(sum(rolls) for _, rolls in rolls_by_dice),
            addition=command.addition,
            number_of_dice_rolled=sum(len(rolls) for _, rolls in rolls_by_dice)
        )

    @staticmethod
    def perform_roll(roll: RollDescription) -> typing.List[int]:
        return [random.randint(1, roll.sides) for _ in range(roll.dice)]

    @staticmethod
    def parse_command(relevant_content) -> typing.Optional[RollCommand]:
        words = relevant_content.split()
        if len(words) != 2 or words[0].lower() != 'roll':
            return None

        pattern = re.compile(r'(?:(\d+)d(\d+))(?:([+-])(\d+)d(\d+))*([-+]\d+)?')
        match = pattern.fullmatch(words[1])
        if match is None:
            return None

        groups = [group for group in match.groups() if group is not None]

        addition = None
        roll_descriptions = [
            RollDescription(int(groups[0]), int(groups[1])),
        ]
        group_index = 2
        while group_index < len(groups):
            token = groups[group_index]
            if token in ('+', '-'):
                roll_descriptions.append(RollDescription(
                    int(groups[group_index + 1]),
                    int(groups[group_index + 2])
                ))
                group_index += 3
            else:
                addition = int(groups[group_index])
                break

        return RollCommand(roll_descriptions, addition)
