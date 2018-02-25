import argparse
import discord
import signal
import sys
import os

from piedotbot.client import MyClient


def main():
    args = get_args()

    if args.token_file is not None:
        token = args.token_file.read().strip()
    elif "BOT_TOKEN" in os.environ:
        token = os.environ.get("BOT_TOKEN", None)
    else:
        print("no bot token provided")
        sys.exit(-1)

    my_bot = discord.Client()
    my_client = MyClient(my_bot, args.state)

    my_bot.on_ready = my_client.on_ready
    my_bot.on_resumed = my_client.on_resumed
    my_bot.on_member_join = my_client.on_member_join
    my_bot.on_message = my_client.on_message
    my_bot.on_message_delete = my_client.on_message_delete
    my_bot.on_message_edit = my_client.on_message_edit
    my_bot.on_reaction_add = my_client.on_reaction_add
    my_bot.on_reaction_remove = my_client.on_reaction_remove
    my_bot.on_voice_state_update = my_client.on_voice_state_update

    signal.signal(signal.SIGTERM, lambda *a: my_client.stop())

    first = True
    while not my_client.exit:
        if not first:
            print("re-running client because it didn't actually ask to exit?")
        first = False
        my_bot.run(token)


def get_args():
    parser = argparse.ArgumentParser(
        description="silly experiment into discord bot implementation"
    )
    parser.add_argument(
        '--token_file', type=argparse.FileType('r'), default=None,
        help='path to file containing discord API token for bot to authenticate with'
    )
    parser.add_argument(
        '-s', '--state', type=str, default="./state.json",
        help='path to file to read/write persistent state to/from'
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
