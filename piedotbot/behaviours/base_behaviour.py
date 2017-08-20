

class Behaviour(object):

    def __init__(self):
        self.allowed_channels = None

    def allowed_in_channel(self, channel):
        allowed = True
        if self.allowed_channels is not None:
            allowed = channel.is_private or channel.name in self.allowed_channels
        return allowed

    async def on_ready(self, client):
        pass

    async def on_resumed(self, client):
        pass

    async def on_member_join(self, client, member):
        pass

    async def on_raw_message(self, client, message):
        pass

    async def on_command(self, client, original_msg, relevant_content):
        pass

    async def on_message_delete(self, client, message):
        pass

    async def on_message_edit(self, client, before, after):
        pass

    async def on_reaction_add(self, client, reaction, user):
        pass

    async def on_reaction_remove(self, client, reaction, user):
        pass

    async def on_voice_state_update(self, client, before, after):
        pass
