from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    def __init__(self):
        super().__init__()
        self.allowed_channels = ["bot-shennanigans"]

    async def on_command(self, client, original_msg, relevant_content):
        words = relevant_content.split()
        if len(words) > 0:
            author = original_msg.author.mention

            response = None

            first_word = words[0].lower()
            if first_word == 'ping':
                response = "pong!"
            elif first_word == 'pong':
                response = "...ping?"
            elif first_word.startswith("ping") or first_word.startswith("pong"):
                response = "now you're just being silly."

            if response is not None:
                await client.bot.send_message(original_msg.channel, f"{author}: {response}")
