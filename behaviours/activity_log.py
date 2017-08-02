import datetime


from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    async def on_voice_state_update(self, client, before, after):
        log_channel = self._find_log_channel(before.server)
        if log_channel is None:
            return

        changes = []
        if before.status != after.status:
            changes.append("changed status from {} to {}".format(before.status, after.status))
        if before.voice.voice_channel is not None and after.voice.voice_channel is None:
            changes.append("left voice channel {}".format(before.voice.voice_channel.name))
        if before.voice.voice_channel is None and after.voice.voice_channel is not None:
            changes.append("joined voice channel {}".format(after.voice.voice_channel.name))
        if before.voice.voice_channel is not None and after.voice.voice_channel is not None and\
                before.voice.voice_channel.name != after.voice.voice_channel.name:
            changes.append("switched voice channel from {} to {}".format(
                before.voice.voice_channel.name,
                after.voice.voice_channel.name
            ))
        if before.status != after.status:
            changes.append("changed status from {} to {}".format(before.status, after.status))

        if len(changes) < 1:
            return

        message = "{} {}".format(
            before.name,
            ", ".join(changes)
        )
        await client.bot.send_message(log_channel, message, tts=True)

    def _find_log_channel(self, server):
        for channel in server.channels:
            if channel.name == "activity_log":
                return channel
        return None
