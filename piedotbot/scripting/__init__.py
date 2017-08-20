import inspect
import typing


from . import interpreter
from . import parser


class Script(object):

    def __init__(self, tokens, source):
        self._builtins = make_builtins()
        self.context = interpreter.Context(tokens, source)

    def run_until_done(self, max_cycles=None):
        while not self.done():
            if self.context.cycles >= max_cycles:
                raise interpreter.InterpreterException("exceeded max cycle count")
            self.advance()

    def advance(self, steps=1):
        for _ in range(steps):
            if self.done():
                break
            token = self.context.next_token()
            self.context.step(self._builtins, token)

    def done(self):
        return self.context.done()

    @staticmethod
    def from_text(text):
        tokens = parser.parse(text)
        print("parsed script: {}".format(tokens))
        return Script(tokens, text)


def make_builtins() -> typing.Dict[str, interpreter.Node]:
    result = {}
    for value in dir(interpreter):
        thing = getattr(interpreter, value)
        if not inspect.isclass(thing):
            continue
        if thing is interpreter.Node:
            continue
        if issubclass(thing, interpreter.Node):
            instance = thing()
            result[instance.word] = instance
    return result
