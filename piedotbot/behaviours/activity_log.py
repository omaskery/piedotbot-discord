from piedotbot.name_util import display_user_display_names
from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_voice_state_update(self, client, before, after):
        log_channel = self._find_log_channel(before.server)
        if log_channel is None:
            return

        changes = []

        if before.status != after.status:
            changes.append(f"changed status from {before.status} to {after.status}")

        def extract_channel_mention(state):
            if state.voice.voice_channel is not None:
                return state.voice.voice_channel.mention
            return None

        before_channel_mention = extract_channel_mention(before)
        after_channel_mention = extract_channel_mention(after)
        if before_channel_mention is not None and after_channel_mention is not None:
            if before_channel_mention != after_channel_mention:
                changes.append(f"switched voice channel from {before_channel_mention} to {after_channel_mention}")
        elif before_channel_mention is not None:
            changes.append(f"left voice channel {before_channel_mention}")
        elif after_channel_mention is not None:
            changes.append(f"joined voice channel {after_channel_mention}")

        if before.display_name != after.display_name:
            changes.append(f"changed display name from {before.display_name}")

        if len(changes) < 1:
            return

        message = f"{display_user_display_names(after)} {', '.join(changes)}"
        await client.bot.send_message(log_channel, message, tts=True)

    @staticmethod
    def _find_log_channel(server):
        for channel in server.channels:
            if channel.name == "activity_log":
                return channel
        return None
