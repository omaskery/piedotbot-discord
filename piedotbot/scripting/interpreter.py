import typing
import random
import copy


from . import parser


class InterpreterException(Exception):
    def __init__(self, message, stack=None, index=None, source=None):
        super().__init__(message)
        self.index = index
        self.stack = stack
        self.source = source


class Workings(object):

    def __init__(self):
        self._workings = []

    def record(self, workings, result, stack):
        self._workings.append((workings, result, copy.deepcopy(stack)))

    def done(self, show_stack=False):
        return "{}.".format("\n".join([
            ">>> {}\n  {}{}".format(
                workings,
                result,
                "\n#  stack: {}".format(stack) if show_stack else "",
            )
            for workings, result, stack in self._workings
        ]))

    def __len__(self):
        return len(self._workings)


class ExecutionInfo(object):

    def __init__(self, tokens, source):
        self.inst_ptr = 0
        self.tokens = tokens
        self.source = source


class Context(object):

    def __init__(self, code, source):
        self.exec_stack = [ExecutionInfo(code, source)]
        self.stack = []
        self.workings = Workings()
        self.cycles = 0
        self.fn_dict = {}

        self._inhibit_advance = False

    @property
    def current_source(self):
        return self.exec_stack[-1].source if len(self.exec_stack) > 0 else None

    def next_token(self):
        top = self.exec_stack[-1]
        return top.tokens[top.inst_ptr]

    def push_exec_stack(self, tokens, source):
        self._inhibit_advance = True
        if len(tokens) > 0:
            self.exec_stack.append(ExecutionInfo(tokens, source))

    def advance(self):
        if self._inhibit_advance:
            self._inhibit_advance = False
        else:
            top = self.exec_stack[-1]
            top.inst_ptr += 1
            if top.inst_ptr >= len(top.tokens):
                self.pop_exec_stack()

    def pop_exec_stack(self):
        return self.exec_stack.pop()

    def record(self, workings, result):
        self.workings.record(workings, result, self.stack)

    def done(self):
        return len(self.exec_stack) < 1

    def step(self, builtins, token):
        if token.typ in (parser.TokenType.INTEGER, parser.TokenType.FLOAT, parser.TokenType.STRING, parser.TokenType.QUOTE):
            self.stack.append(token.value)
        elif token.typ == parser.TokenType.WORD:
            builtin = builtins.get(token.value.upper(), None)
            user_fn = self.fn_dict.get(token.value.upper(), None)
            if builtin is not None:
                stack_before = copy.deepcopy(self.stack)
                try:
                    builtin.evaluate(self)
                except InterpreterException as exc:
                    exc.index = token.index
                    exc.stack = stack_before
                    exc.source = self.exec_stack[-1].source if len(self.exec_stack) > 0 else None
                    raise exc
            elif user_fn is not None:
                self.advance()
                self.push_exec_stack(user_fn.tokens, user_fn.source)
            else:
                raise InterpreterException("unknown word {}".format(token.value), token.index)
        else:
            raise InterpreterException(
                "unknown token type: {} (value={})".format(token.typ, token.value),
                token.index
            )
        self.advance()
        self.cycles += 1


class Node(object):

    def __init__(self, word):
        self.word = word

    def _ensure_stack_size(self, stack, expected_types) -> typing.Union[typing.Any, typing.List[typing.Any]]:
        count = len(stack)
        n = len(expected_types)
        if count < n:
            raise InterpreterException("{word} requires {n} values on the stack, only {count} found".format(
                word=self.word,
                n=n,
                count=count
            ))
        values = pop_many(stack, n, in_order=True)
        for index, (value, expected_type) in enumerate(zip(values, expected_types)):
            if expected_type is not None:
                try:
                    expected_type(value)
                except Exception:
                    raise InterpreterException(
                        "{word} requires that parameter {index} is of type {type.__name__}, got type {actual}".format(
                            word=self.word,
                            index=index+1,
                            type=expected_type,
                            actual=type(value).__name__
                        )
                    )
        print(" args to {}: {}".format(self.word, values))
        if n > 1:
            return tuple(values)
        else:
            return values[0]

    def evaluate(self, context: Context):
        _ = self
        context.record("unimplemented", None)
        raise NotImplemented("abstract node has no default evaluate behaviour")


class NopNode(Node):

    def __init__(self):
        super().__init__("NOP")

    def evaluate(self, context: Context):
        pass


class DupNode(Node):

    def __init__(self):
        super().__init__("DUP")

    def evaluate(self, context: Context):
        top = self._ensure_stack_size(context.stack, [None])
        context.stack.append(top)
        context.stack.append(copy.deepcopy(top))
        context.record("duplicating the top of the stack", top)


class SwapNode(Node):

    def __init__(self):
        super().__init__("SWAP")

    def evaluate(self, context: Context):
        under_top, top = self._ensure_stack_size(context.stack, [None, None])
        context.stack.append(top)
        context.stack.append(under_top)
        context.record("swapping top 2 stack values", top)


class EvalNode(Node):

    def __init__(self):
        super().__init__("EVAL")

    def evaluate(self, context: Context):
        quoted = self._ensure_stack_size(context.stack, [quote_type])
        context.advance()
        context.push_exec_stack(quoted, context.current_source)


class DefunNode(Node):

    def __init__(self):
        super().__init__("DEFUN")

    def evaluate(self, context: Context):
        name, quoted = self._ensure_stack_size(context.stack, [str, quote_type])
        source = "{} \"{}\" [ {} ];".format(self.word, name, " ".join(map(lambda q: q.original_str(), quoted)))
        context.fn_dict[name] = parser.UserFunction(source, quoted, name)
        print("defined {} as {}".format(name, quoted))


class RepeatNode(Node):

    def __init__(self):
        super().__init__("REPEAT")

    def evaluate(self, context: Context):
        count, quoted = self._ensure_stack_size(context.stack, [int, quote_type])
        context.advance()
        for _ in range(count):
            context.push_exec_stack(quoted, context.current_source)


class DiceRollNode(Node):

    def __init__(self):
        super().__init__("ROLL")

    def evaluate(self, context: Context):
        number, sides = self._ensure_stack_size(context.stack, [int, int])
        if sides < 1:
            raise InterpreterException("unable to roll a {n} sided dice".format(n=sides))
        if number < 1:
            raise InterpreterException("must be rolling at least 1 dice")
        if number > 40:
            raise InterpreterException("refusing to roll more than 40 dice in a single operation >:C")
        rolls = [random.randint(1, sides) for _ in range(number)]
        context.stack.append(rolls)
        context.record("rolled {}d{} giving".format(number, sides), rolls)


class MultiplyNode(Node):

    def __init__(self):
        super().__init__("MUL")

    def evaluate(self, context: Context):
        a, b = self._ensure_stack_size(context.stack, [float, float])
        result = a * b
        context.stack.append(result)
        context.record("{} times {} is".format(a, b), result)


class DivideNode(Node):

    def __init__(self):
        super().__init__("DIV")

    def evaluate(self, context: Context):
        a, b = self._ensure_stack_size(context.stack, [float, float])
        result = a / b
        context.stack.append(result)
        context.record("{} divided by {} is".format(a, b), result)


class AddNode(Node):

    def __init__(self):
        super().__init__("ADD")

    def evaluate(self, context: Context):
        a, b = self._ensure_stack_size(context.stack, [float, float])
        result = a + b
        context.stack.append(result)
        context.record("{} plus {} is".format(a, b), result)


class SubtractNode(Node):

    def __init__(self):
        super().__init__("SUB")

    def evaluate(self, context: Context):
        a, b = self._ensure_stack_size(context.stack, [float, float])
        result = a - b
        context.stack.append(result)
        context.record("{} subtract {} is".format(a, b), result)


class TotalNode(Node):

    def __init__(self):
        super().__init__("TOTAL")

    def evaluate(self, context: Context):
        values = self._ensure_stack_size(context.stack, [iterable_type])
        try:
            total = sum(values)
        except Exception as ex:
            print("could not sum values in TOTAL: {}".format(ex))
            raise InterpreterException("total requires values in iterable on top of stack to be summable")
        context.stack.append(total)
        context.record("totalling", total)


class TopNode(Node):

    def __init__(self):
        super().__init__("TOP")

    def evaluate(self, context: Context):
        collection, count = self._ensure_stack_size(context.stack, [iterable_type, int])
        result = sorted(collection, reverse=True)[:count]
        context.stack.append(result)
        context.record("the top {} values are".format(count), result)


class MaxNode(Node):

    def __init__(self):
        super().__init__("MAX")

    def evaluate(self, context: Context):
        collection = self._ensure_stack_size(context.stack, [iterable_type])
        result = max(collection)
        context.stack.append(result)
        context.record("the maximum is", result)


class ListNode(Node):

    def __init__(self):
        super().__init__("LIST")

    def evaluate(self, context: Context):
        length = self._ensure_stack_size(context.stack, [int])
        if length < 0:
            raise InterpreterException("LIST requires a non-negative length parameter")
        if len(context.stack) < length:
            raise InterpreterException("LIST cannot take {} values from stack, only {} values available".format(
                length, len(context.stack)
            ))
        result = pop_many(context.stack, length, in_order=True)
        context.stack.append(result)
        context.record("turned top {length} values on stack into a list:".format(
            length=length,
        ), result)


def pop_many(stack, n, in_order=False):
    result = [stack.pop() for _ in range(n)]
    if in_order:
        result = list(reversed(result))
    return result


def iterable_type(value):
    if not hasattr(value, '__iter__'):
        raise TypeError("not iterable")


def quote_type(value):
    iterable_type(value)
    if not all([isinstance(v, parser.Token) for v in value]):
        raise TypeError("not iterable")

