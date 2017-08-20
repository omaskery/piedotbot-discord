from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    def __init__(self):
        super().__init__()
        self.allowed_channels = ["bot-shennanigans"]

    async def on_command(self, client, original_msg, relevant_content):
        words = relevant_content.split()
        if len(words) > 0:
            if words[0].lower() == 'ping':
                await client.bot.send_message(original_msg.channel, "{}: pong!".format(original_msg.author.mention))
            elif words[0].lower() == 'pong':
                await client.bot.send_message(original_msg.channel, "{}: ...ping?".format(original_msg.author.mention))
            elif words[0].lower().startswith("ping") or words[0].lower().startswith("pong"):
                await client.bot.send_message(original_msg.channel, "{}, now you're just being silly.".format(
                    original_msg.author.mention
                ))
