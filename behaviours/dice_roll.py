import datetime
import asyncio
import random
import re


from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_command(self, client, original_msg, relevant_content):
        author = original_msg.author
        words = relevant_content.split()
        if len(words) > 1 and words[0].lower() == 'roll':
            max_visible_dice = 40
            sleep_interval = datetime.timedelta(seconds=3.0)
            sleep_period = 0.01
            max_calculation_time = datetime.timedelta(minutes=1)
            min_progress_msg_time = datetime.timedelta(seconds=10)

            pattern = re.compile(r'(\d+)d(\d+)')
            match = pattern.fullmatch(words[1])
            if match is not None:
                dice, sides = int(match.group(1)), int(match.group(2))
                if dice > 100000:
                    warning = '{author.mention} hold up, I need to go think about this...'.format(author=author)
                    await client.bot.send_message(original_msg.channel, warning)

                total = 0
                rolls = []
                given_eta = False
                start_time = datetime.datetime.now()
                next_interval = start_time + sleep_interval
                given_up = False
                for index in range(dice):
                    roll_result = random.randint(1, sides)
                    if dice <= max_visible_dice:
                        rolls.append(roll_result)
                    total += roll_result

                    now = datetime.datetime.now()
                    if now >= next_interval:
                        next_interval += sleep_interval

                        print("  calculating {}/{} ({}%)".format(
                            index, dice, round(index / dice * 100, 3)
                        ))

                        if not given_eta:
                            time_so_far = now - start_time
                            time_per_dice = time_so_far.total_seconds() / index
                            dice_to_go = int(dice - (index + 1))
                            seconds_remaining = time_per_dice * dice_to_go
                            intervals = (
                                ('seconds', 1), ('minutes', 60.0), ('hours', 60.0), ('days', 24.0),
                            )
                            time_to_go = None
                            unit_of_time_remaining = seconds_remaining
                            for interval in intervals:
                                interval_name, interval_divider = interval
                                unit_of_time_remaining /= interval_divider
                                try:
                                    time_to_go = datetime.timedelta(**{interval_name: unit_of_time_remaining})
                                    break
                                except OverflowError:
                                    time_to_go = None
                            if time_to_go is not None:
                                print("time to go:", time_to_go)
                                progress_msg = "{author.mention}, yeah... it's looking like {roll} is gonna take another {remaining} to figure out...".format(
                                    author=author,
                                    roll=words[1],
                                    remaining=time_to_go
                                )
                                if time_to_go >= max_calculation_time:
                                    progress_msg += " and I can't be bothered to do that. I give up."
                                    given_up = True
                                if time_to_go > min_progress_msg_time:
                                    await client.bot.send_message(original_msg.channel, progress_msg)
                                if given_up:
                                    break
                            else:
                                progress_msg = "{author.mention}, it's hard to even guess how long that will take, so I'm not gonna bother with that one. I give up.".format(
                                    author=author
                                )
                                await client.bot.send_message(original_msg.channel, progress_msg)
                                given_up = True
                                break
                            given_eta = True
                        await asyncio.sleep(sleep_period)

                if not given_up:
                    average = total / dice
                    msg = '{author.mention} rolled {rolls} for a total of {total} and average of {average}'.format(
                        author=author,
                        rolls="[{}]".format(", ".join(map(str, rolls))) if dice <= max_visible_dice else "{} dice".format(dice),
                        total=total,
                        average=average
                    )
                    await client.bot.send_message(original_msg.channel, msg)
