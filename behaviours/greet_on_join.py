

from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_member_joined(self, client, member):
        users = set(client.state.get("users", []))

        if member.name not in users:
            users.add(member.name)
            client.state["users"] = list(users)
            msg = 'Welcome to {server.name}, {member.mention}'.format(server=member.server, member=member)
        else:
            msg = 'Welcome back, {member.mention} :)'.format(member=member)

        await client.bot.send_message(member.server, msg)

