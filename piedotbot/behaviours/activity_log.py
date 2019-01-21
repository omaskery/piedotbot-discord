from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_voice_state_update(self, client, before, after):
        log_channel = self._find_log_channel(before.server)
        if log_channel is None:
            return

        changes = []

        if before.status != after.status:
            changes.append(f"changed status from {before.status} to {after.status}")

        before_channel_name = before.voice.voice_channel.name if before.voice.voice_channel else None
        after_channel_name = after.voice.voice_channel.name if after.voice.voice_chanel else None
        if before_channel_name is not None and after_channel_name is not None:
            changes.append(f"switched voice channel from {before_channel_name} to {after_channel_name}")
        elif before_channel_name is not None:
            changes.append(f"left voice channel {before_channel_name}")
        elif after_channel_name is not None:
            changes.append(f"joined voice channel {after_channel_name}")

        if len(changes) < 1:
            return

        message = f"{before.name} {', '.join(changes)}"
        await client.bot.send_message(log_channel, message, tts=True)

    @staticmethod
    def _find_log_channel(server):
        for channel in server.channels:
            if channel.name == "activity_log":
                return channel
        return None
