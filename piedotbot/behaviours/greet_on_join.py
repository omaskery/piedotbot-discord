

from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_member_join(self, client, member):
        msg = f'Welcome to {member.server.name}, {member.mention}!'
        await client.bot.send_message(member.server, msg)

