import argparse
import discord
import string
import json


import behaviours


class MyClient(object):
    def __init__(self, bot, state_path):
        self.bot = bot
        self.behaviours = behaviours.build_behaviours()

        self.state = {}
        self._state_path = state_path

    def _load_state(self):
        try:
            with open(self._state_path, 'r') as fp:
                self.state = json.load(fp)
        except FileNotFoundError:
            self.state = {}

    def _save_state(self):
        with open(self._state_path, 'w') as fp:
            json.dump(self.state, fp)

    async def on_ready(self):
        print("client logged in as {bot.user.name} with ID {bot.user.id}".format(bot=self.bot))
        print("  activation phrase: {}".format(self.bot.user.mention))

        self._load_state()
        for behaviour in self.behaviours:
            await behaviour.on_ready(self)
            self._save_state()

    async def on_resumed(self):
        print("resumed")

        self._load_state()
        for behaviour in self.behaviours:
            await behaviour.on_resumed(self)
            self._save_state()

    async def on_member_join(self, member):
        print("member joined: {}".format(member.name))
        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_member_join(self, member))
            self._save_state()

    async def on_message(self, message):
        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_raw_message(self, message))
            self._save_state()

        activation_phrases = [self.bot.user.mention, "!", self.bot.user.name]

        print("[{}] {}".format(message.author, message.content))

        if message.author == self.bot.user:
            return

        ref_to_self = None
        relevant_content = None
        for activation_phrase in activation_phrases:
            possible_ref_to_self = message.content.find(activation_phrase)

            if possible_ref_to_self != -1:
                relevant_content = message.content[possible_ref_to_self + len(activation_phrase):]
                while len(relevant_content) > 0 and relevant_content[0] in string.punctuation:
                    relevant_content = relevant_content[1:]
                relevant_content = relevant_content.strip()

                if len(relevant_content) > 0:
                    ref_to_self = possible_ref_to_self
                    break
        if ref_to_self is None:
            return

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_command(self, message, relevant_content))
            self._save_state()

    async def on_message_delete(self, message):
        print("message deleted:", message)

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_message_delete(self, message))
            self._save_state()

    async def on_message_edit(self, before, after):
        print("message edited")
        print("  before:", before)
        print("  after:", after)

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_message_edit(self, before, after))
            self._save_state()

    async def on_reaction_add(self, reaction, user):
        print("reaction added '{}' by {}".format(reaction, user))

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_reaction_add(self, reaction, user))
            self._save_state()

    async def on_reaction_remove(self, reaction, user):
        print("reaction removed '{}' by {}".format(reaction, user))

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_reaction_remove(self, reaction, user))
            self._save_state()

    async def on_voice_state_update(self, before, after):
        print("voice state changed {} -> {}".format(before, after))

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_voice_state_update(self, before, after))
            self._save_state()


def main():
    args = get_args()

    token = args.token_file.read().strip()

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

    my_bot.run(token)


def get_args():
    parser = argparse.ArgumentParser(
        description="silly experiment into discord bot implementation"
    )
    parser.add_argument(
        'token_file', type=argparse.FileType('r'),
        help='path to file containing discord API token for bot to authenticate with'
    )
    parser.add_argument(
        '-s', '--state', type=str, default="./state.json",
        help='path to file to read/write persistent state to/from'
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
