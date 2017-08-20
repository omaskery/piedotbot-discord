import traceback
import typing
import string
import enum


@enum.unique
class TokenType(enum.Enum):
    INTEGER = enum.auto()
    FLOAT = enum.auto()
    STRING = enum.auto()
    START_QUOTE = enum.auto()
    END_QUOTE = enum.auto()
    QUOTE = enum.auto()
    END_STMNT = enum.auto()
    WORD = enum.auto()


class Token(object):
    def __init__(self, typ, value, index):
        self.typ = typ
        self.value = value
        self.index = index

    def __str__(self):
        return "Token({}, {}, @{})".format(self.typ, self.value, self.index)

    def original_str(self):
        if self.typ in (TokenType.INTEGER, TokenType.FLOAT):
            return str(self.value)
        elif self.typ == TokenType.STRING:
            return '"{}"'.format(self.value)
        elif self.typ == TokenType.WORD:
            return self.value
        elif self.typ == TokenType.QUOTE:
            return '[ {} ]'.format(", ".join(map(lambda x: x.original_str(), self.value)))
        elif self.typ == TokenType.START_QUOTE:
            return "["
        elif self.typ == TokenType.END_QUOTE:
            return "]"
        raise Exception("unknown token type for turning to string: {}?".format(self.typ))

    def __repr__(self):
        return self.__str__()

    def serialise(self):
        if self.typ == TokenType.QUOTE:
            value = [q.serialise() for q in self.value]
        else:
            value = self.value
        return {
            "type": self.typ.name,
            "value": value,
            "index": self.index,
        }

    @staticmethod
    def deserialise(blob):
        typ = TokenType[blob["type"]]
        if typ == TokenType.QUOTE:
            value = [Token.deserialise(b) for b in blob["value"]]
        else:
            value = blob["value"]
        return Token(
            typ,
            value,
            blob["index"]
        )


class UserFunction(object):

    def __init__(self, source, tokens, name):
        self.name = name
        self.tokens = tokens
        self.source = source

    def serialise(self):
        return {
            "name": self.name,
            "tokens": [token.serialise() for token in self.tokens],
            "source": self.source,
        }

    @staticmethod
    def deserialise(blob):
        return UserFunction(
            blob["source"],
            [Token.deserialise(b) for b in blob["tokens"]],
            blob["name"]
        )


class ParseException(Exception):
    def __init__(self, message, index):
        super().__init__(message)
        self.index = index


def parse(text):
    parser = Parser(text)
    return parser.parse()


class Parser(object):

    def __init__(self, source):
        self.source = source
        self._index = 0
        self._next_token = typing.cast(typing.Optional[Token], None)

        class TracedMethod(object):
            def __init__(self, parser, method):
                self._parser = parser
                self._method = method

            def __call__(self, *args, **kwargs):
                return self._parser.trace_call(self._method, *args, **kwargs)

        if False:
            self._indent = 0
            for member_name in dir(self):
                member = getattr(self, member_name)
                if not member_name.startswith("__") and hasattr(member, "__call__") and member_name != "trace_call":
                    print("callable:", member_name)
                    setattr(self, member_name, TracedMethod(self, member))

    def trace_call(self, fn, *args, **kwargs):
        display_args = list(map(str, args))
        display_args.extend([
            "{}={}".format(k, v)
            for k, v in kwargs.items()
        ])
        indent_str = "  |"
        print("{}--{}({})".format(
            self._indent * indent_str,
            fn.__name__,
            ", ".join(display_args),
        ))
        self._indent += 1
        call_result = fn(*args, **kwargs)
        self._indent -= 1
        print("{}->{} returned {}".format(
            self._indent * indent_str,
            fn.__name__,
            call_result
        ))
        return call_result

    def parse(self):
        statements = []
        self._parse_statement_list(statements)
        return statements

    def _error(self, token: typing.Optional[typing.Union[Token, int]], message: str, *args, **kwargs):
        index = len(self.source)
        if token is not None:
            if isinstance(token, int):
                index = token
            elif isinstance(token, Token):
                index = token.index
            else:
                raise Exception("invalid type passed as token")
        text = "[{}]: {}".format(
            index, message.format(*args, **kwargs)
        )
        print("parser exception:")
        print("  token:", token)
        print("  message:", text)
        print("  traceback:")
        traceback.print_stack()
        raise ParseException(text, index)

    def _parse_statement_list(self, statements):
        first = True
        while self._peek_token() is not None and self._peek_token().typ != TokenType.END_QUOTE:
            if not first:
                self._expect_token(TokenType.END_STMNT)
            first = False
            self._parse_statement(statements)

    def _parse_statement(self, statements):
        if self._peek_token() is not None:
            word = self._parse_word()
            params = []
            while not self._peek_token() is None and self._peek_token().typ not in (TokenType.END_STMNT, TokenType.END_QUOTE):
                check = self._parse_token()
                params.append(check)
            statements.extend(params)
            statements.append(word)

    def _parse_word(self):
        return self._expect_token(TokenType.WORD)

    def _parse_token(self):
        next = self._peek_token()
        valid_tokens = (
            TokenType.WORD, TokenType.STRING, TokenType.INTEGER, TokenType.FLOAT
        )
        if next is not None and next.typ == TokenType.START_QUOTE:
            result = self._parse_quote()
        elif next is None or next.typ not in valid_tokens:
            self._error(next, "expected token in {}, got {}", valid_tokens, next.typ)
        else:
            result = self._read_token()
        return result

    def _parse_quote(self):
        result = []
        start = self._expect_token(TokenType.START_QUOTE)
        self._parse_statement_list(result)
        self._expect_token(TokenType.END_QUOTE)
        return Token(TokenType.QUOTE, result, start.index)

    def _expect_token(self, typ):
        check = self._read_token()
        if check is None or check.typ != typ:
            self._error(
                check,
                "expected token of type {}, got {}",
                typ,
                check.typ if check is not None else None
            )
        return check

    def _read_token(self):
        result = self._peek_token()
        self._next_token = None
        return result

    def _peek_token(self) -> typing.Optional[Token]:
        if self._next_token is None:
            self._next_token = self._actually_get_next_token()
        return self._next_token

    def _actually_get_next_token(self):
        result = None
        self._skip_whitespace()
        if not self._is_eof():
            self._skip_whitespace()
            first = self._peek()
            if first == '"':
                result = self._read_string()
            elif first == '[':
                result = self._read_start_quote()
            elif first == ']':
                result = self._read_end_quote()
            elif first == ';':
                result = self._read_end_statement()
            elif first in (string.digits + "-"):
                result = self._read_number_literal()
            else:
                result = self._read_word()
            self._skip_whitespace()
        return result

    def _read_string(self):
        index = self._index
        if self._get() != '"':
            self._error(index, "string expected to start with '\"' symbol")
        result = ""
        while not self._is_eof() and not self._peek() == '"':
            check = self._get()
            if check == '\\':
                special = self._get()
                specials = {
                    'n': '\n', 't': '\t', '\\': '\\'
                }
                if special in specials.keys():
                    result += specials[special]
                else:
                    self._error(check, "'\\{}' is an invalid escape character", special)
            else:
                result += check
        if self._is_eof():
            self._error(self._index, "unexpected end of input, did you forget a '\"' at the end of a string?")
        index = self._index
        if self._get() != '"':
            self._error(index, "strings must end with a '\"'")
        return Token(TokenType.STRING, result, index)

    def _read_start_quote(self):
        index = self._index
        if self._get() != '[':
            self._error(index, "quote expected to start with '[' symbol")
        return Token(TokenType.START_QUOTE, None, index)

    def _read_end_quote(self):
        index = self._index
        if self._get() != ']':
            self._error(index, "quote expected to end with ']' symbol")
        return Token(TokenType.END_QUOTE, None, index)

    def _read_end_statement(self):
        index = self._index
        if self._get() != ';':
            self._error(index, "statement expected to end with ';' symbol")
        return Token(TokenType.END_STMNT, None, index)

    def _read_number_literal(self):
        index = self._index
        seen_dot = False
        result = ""
        first = True
        while not self._is_eof():
            check = self._peek()
            if check in string.digits or (not seen_dot and check == '.') or (first and check == '-'):
                if check == '.':
                    seen_dot = True
                result += self._get()
            else:
                break
            first = False
        if seen_dot:
            result = Token(TokenType.FLOAT, float(result), index)
        else:
            result = Token(TokenType.INTEGER, int(result), index)
        return result

    def _read_word(self):
        index = self._index
        result = ""
        terminating_chars = string.whitespace + ";[]"
        while not self._is_eof() and self._peek() not in terminating_chars:
            result += self._get()
        return Token(TokenType.WORD, result, index)

    def _skip_whitespace(self):
        while not self._is_eof() and self._peek() in string.whitespace:
            self._get()

    def _is_eof(self):
        return self._index >= len(self.source)

    def _peek(self):
        if self._index < len(self.source):
            return self.source[self._index]
        else:
            return None

    def _get(self):
        result = self._peek()
        if result is not None:
            self._index += 1
        return result
