

from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_member_join(self, client, member):
        msg = 'Welcome to {server.name}, {member.mention}!'.format(server=member.server, member=member)
        await client.bot.send_message(member.server, msg)

