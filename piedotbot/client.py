

import asyncio
import string


from . import persistence
from . import behaviours


class MyClient(object):
    def __init__(self, bot, db_url):
        self.bot = bot
        self.behaviours = behaviours.build_behaviours()
        self.db_url = db_url
        self.db = persistence.db

        self.state = {}
        self.exit = False

    def stop(self):
        print("exit requested")
        self.exit = True
        loop = asyncio.get_event_loop()
        loop.create_task(self.bot.logout())

    async def on_ready(self):
        print(f"client logged in as {self.bot.user.name} with ID {self.bot.user.id}")
        print(f"  activation phrase: {self.bot.user.mention}")

        print(f"connecting to database [{self.db_url}]...")
        await self.db.set_bind(self.db_url)
        print("connected to database :)")

        for behaviour in self.behaviours:
            await behaviour.on_ready(self)

    async def on_resumed(self):
        print("resumed")

        for behaviour in self.behaviours:
            await behaviour.on_resumed(self)

    async def on_member_join(self, member):
        print(f"member joined: {member.name}")
        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_member_join(self, member))

    async def on_message(self, message):
        for behaviour in self.behaviours:
            if behaviour.allowed_in_channel(message.channel):
                self.bot.loop.create_task(behaviour.on_raw_message(self, message))

        activation_phrases = [self.bot.user.mention, "!", self.bot.user.name]

        print(f"[{message.author}] {message.content}")

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
            if behaviour.allowed_in_channel(message.channel):
                self.bot.loop.create_task(behaviour.on_command(self, message, relevant_content))

    async def on_message_delete(self, message):
        print(f"message deleted: {message!r}")

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_message_delete(self, message))

    async def on_message_edit(self, before, after):
        print("message edited")
        print(f"  before: {before!r}")
        print(f"  after: {after!r}")

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_message_edit(self, before, after))

    async def on_reaction_add(self, reaction, user):
        print(f"reaction added '{reaction!r}' by {user!r}")

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_reaction_add(self, reaction, user))

    async def on_reaction_remove(self, reaction, user):
        print(f"reaction removed '{reaction!r}' by {user!r}")

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_reaction_remove(self, reaction, user))

    async def on_voice_state_update(self, before, after):
        print(f"voice state changed {before!r} -> {after!r}")

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_voice_state_update(self, before, after))
