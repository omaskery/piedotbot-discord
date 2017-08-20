import typing


from ..scripting.interpreter import InterpreterException
from ..scripting.parser import ParseException
from .. import scripting
from . import base_behaviour


class Behaviour(base_behaviour.Behaviour):

    def __init__(self):
        super().__init__()
        self.allowed_channels = ["bot-shennanigans"]

        self._fn_dict = None

    async def on_command(self, client, original_msg, relevant_content):
        author = original_msg.author
        words = relevant_content.split(maxsplit=1)
        trigger_words = ['eval', 'eval?', 'eval??']

        state_key = "stored_script_functions"

        if self._fn_dict is None:
            if state_key not in client.state:
                client.state[state_key] = {}
            self._fn_dict = dict([
                (k, scripting.parser.UserFunction.deserialise(v))
                for k, v in client.state[state_key].items()
            ])

        if len(words) > 1 and words[0].lower() in trigger_words:
            script_source = words[1]
            try:
                script = scripting.Script.from_text(script_source)
                script.context.fn_dict = self._fn_dict
                script.run_until_done(max_cycles=1000)
                show_stack = words[0].lower() == 'eval??'
                show_workings = words[0].lower() != 'eval' and len(script.context.workings) > 0
                msg = '{author.mention} result={result} (cycles={cycles}){workings}'.format(
                    author=author,
                    result=script.context.stack[-1] if len(script.context.stack) > 0 else "<no result>",
                    workings="" if not show_workings else "```python\n{}```\n".format(
                        script.context.workings.done(show_stack)
                    ),
                    cycles=script.context.cycles
                )
                await client.bot.send_message(original_msg.channel, msg)
            except ParseException as exc:
                await Behaviour._show_error(original_msg.channel, client, author, 'parser', script_source, exc)
            except InterpreterException as exc:
                await Behaviour._show_error(original_msg.channel, client, author, 'interpreter', script_source, exc)

            client.state[state_key] = dict([
                (k, v.serialise())
                for k, v in self._fn_dict.items()
            ])

    @staticmethod
    async def _show_error(channel, client, author, type_name, source, exc: typing.Union[ParseException, InterpreterException]):
        indent = exc.index if exc.index is not None else 0
        show_stack = hasattr(exc, "stack") and exc.stack is not None
        if hasattr(exc, "source"):
            source = exc.source
        explanation = "```\n{source}\n{error}{stack}```".format(
            source=source,
            error="{indent}^ {exc}".format(
                indent=" " * indent,
                exc=exc
            ),
            stack="\nstack before instruction: {}".format(exc.stack) if show_stack else ""
        )
        msg = '{author.mention} {type} error: {explanation}'.format(
            type=type_name,
            author=author,
            exc=exc,
            explanation=explanation
        )
        await client.bot.send_message(channel, msg)

