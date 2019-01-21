import argparse
import asyncio
import discord
import signal
import sys
import os

from piedotbot.client import MyClient


def main():
    print("entering main")

    args = get_args()

    if args.token_file is not None:
        token = args.token_file.read().strip()
    elif "BOT_TOKEN" in os.environ:
        token = os.environ.get("BOT_TOKEN", None)
    else:
        print("no bot token provided")
        sys.exit(-1)

    db_url = os.environ.get("DATABASE_URL")

    print("constructing bot")
    loop = asyncio.get_event_loop()
    my_bot = discord.Client(loop=loop)
    my_client = MyClient(my_bot, db_url)

    my_bot.on_ready = my_client.on_ready
    my_bot.on_resumed = my_client.on_resumed
    my_bot.on_member_join = my_client.on_member_join
    my_bot.on_message = my_client.on_message
    my_bot.on_message_delete = my_client.on_message_delete
    my_bot.on_message_edit = my_client.on_message_edit
    my_bot.on_reaction_add = my_client.on_reaction_add
    my_bot.on_reaction_remove = my_client.on_reaction_remove
    my_bot.on_voice_state_update = my_client.on_voice_state_update

    print("registering signal handler")
    signal.signal(signal.SIGTERM, lambda *a: my_client.stop())

    while not my_client.exit:
        try:
            print("running bot")
            my_bot.loop.run_until_complete(my_bot.start(token))
        except KeyboardInterrupt:
            print("keyboard interrupt")
            loop.run_until_complete(my_bot.logout())

    print("exiting main")


def get_args():
    parser = argparse.ArgumentParser(
        description="silly experiment into discord bot implementation"
    )
    parser.add_argument(
        '--token_file', type=argparse.FileType('r'), default=None,
        help='path to file containing discord API token for bot to authenticate with'
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
