

import asyncio
import string


from . import behaviours


class MyClient(object):
    def __init__(self, bot):
        self.bot = bot
        self.behaviours = behaviours.build_behaviours()

        self.state = {}
        self.exit = False

    def stop(self):
        print("exit requested")
        self.exit = True
        loop = asyncio.get_event_loop()
        loop.create_task(self.bot.logout())

    async def on_ready(self):
        print("client logged in as {bot.user.name} with ID {bot.user.id}".format(bot=self.bot))
        print("  activation phrase: {}".format(self.bot.user.mention))

        for behaviour in self.behaviours:
            await behaviour.on_ready(self)

    async def on_resumed(self):
        print("resumed")

        for behaviour in self.behaviours:
            await behaviour.on_resumed(self)

    async def on_member_join(self, member):
        print("member joined: {}".format(member.name))
        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_member_join(self, member))

    async def on_message(self, message):
        for behaviour in self.behaviours:
            if behaviour.allowed_in_channel(message.channel):
                self.bot.loop.create_task(behaviour.on_raw_message(self, message))

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
            if behaviour.allowed_in_channel(message.channel):
                self.bot.loop.create_task(behaviour.on_command(self, message, relevant_content))

    async def on_message_delete(self, message):
        print("message deleted:", message)

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_message_delete(self, message))

    async def on_message_edit(self, before, after):
        print("message edited")
        print("  before:", before)
        print("  after:", after)

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_message_edit(self, before, after))

    async def on_reaction_add(self, reaction, user):
        print("reaction added '{}' by {}".format(reaction, user))

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_reaction_add(self, reaction, user))

    async def on_reaction_remove(self, reaction, user):
        print("reaction removed '{}' by {}".format(reaction, user))

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_reaction_remove(self, reaction, user))

    async def on_voice_state_update(self, before, after):
        print("voice state changed {} -> {}".format(before, after))

        for behaviour in self.behaviours:
            self.bot.loop.create_task(behaviour.on_voice_state_update(self, before, after))
