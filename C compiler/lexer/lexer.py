from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator

from .tokens import KEYWORDS, OPERATORS


class TokenType(str, Enum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    STRING = "STRING"
    CHAR = "CHAR"
    OPERATOR = "OPERATOR"
    PUNCTUATOR = "PUNCTUATOR"
    PREPROCESSOR = "PREPROCESSOR"
    COMMENT = "COMMENT"
    EOF = "EOF"


@dataclass(frozen=True)
class SourcePosition:
    line: int
    column: int
    index: int


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    index: int
    literal: object | None = None

    @property
    def position(self) -> SourcePosition:
        return SourcePosition(self.line, self.column, self.index)


class LexerError(SyntaxError):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{message} at line {line}, column {column}")
        self.message = message
        self.line = line
        self.column = column






PUNCTUATORS = frozenset({"(", ")", "{", "}", "[", "]", ";", ",", "."})

INTEGER_SUFFIX_CHARS = frozenset("uUlL")
FLOAT_SUFFIX_CHARS = frozenset("fFlL")


class LexicalAnalyzer:
    """Reusable lexical analyzer for C source code."""

    def __init__(self, source: str, *, keep_comments: bool = False, add_eof: bool = True) -> None:
        self.source = source
        self.keep_comments = keep_comments
        self.add_eof = add_eof
        self.index = 0
        self.line = 1
        self.column = 1
        self._line_has_code = False

    def tokenize(self) -> list[Token]:
        tokens = list(self.iter_tokens())
        if self.add_eof:
            tokens.append(self._make_token(TokenType.EOF, "", literal=None))
        return tokens

    def iter_tokens(self) -> Iterator[Token]:
        while not self._at_end:
            self._skip_whitespace()
            if self._at_end:
                break

            char = self._peek()
            if char == "#" and not self._line_has_code:
                yield self._read_preprocessor()
            elif self._starts_prefixed_literal():
                yield self._read_prefixed_quoted()
            elif self._is_identifier_start(char):
                yield self._read_identifier_or_keyword()
            elif char.isdigit() or (char == "." and self._peek_next().isdigit()):
                yield self._read_number()
            elif char == '"':
                yield self._read_string()
            elif char == "'":
                yield self._read_char()
            elif char == "/" and self._peek_next() in {"/", "*"}:
                comment = self._read_comment()
                if self.keep_comments:
                    yield comment
            else:
                yield self._read_operator_or_punctuator()

    @property
    def _at_end(self) -> bool:
        return self.index >= len(self.source)

    def _make_token(self, token_type: TokenType, lexeme: str, literal: object | None = None) -> Token:
        return Token(token_type, lexeme, self.line, self.column, self.index, literal)

    def _token_from(self, token_type: TokenType, start_line: int, start_column: int, start_index: int, literal: object | None = None) -> Token:
        return Token(token_type, self.source[start_index : self.index], start_line, start_column, start_index, literal)

    def _peek(self, offset: int = 0) -> str:
        at = self.index + offset
        if at >= len(self.source):
            return "\0"
        return self.source[at]

    def _peek_next(self) -> str:
        return self._peek(1)

    def _advance(self) -> str:
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
            self._line_has_code = False
        else:
            self.column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._at_end or self._peek() != expected:
            return False
        self._advance()
        return True

    def _skip_whitespace(self) -> None:
        while not self._at_end:
            char = self._peek()
            if char in " \r\t\f\v":
                self._advance()
            elif char == "\n":
                self._advance()
            else:
                break

    def _read_identifier_or_keyword(self) -> Token:
        start_line, start_column, start_index = self.line, self.column, self.index
        while self._is_identifier_part(self._peek()):
            self._advance()

        lexeme = self.source[start_index : self.index]
        token_type = TokenType.KEYWORD if lexeme in KEYWORDS else TokenType.IDENTIFIER
        self._line_has_code = True
        return Token(token_type, lexeme, start_line, start_column, start_index)

    def _read_number(self) -> Token:
        start_line, start_column, start_index = self.line, self.column, self.index
        token_type = TokenType.INTEGER

        if self._peek() == "0" and self._peek_next() in {"x", "X"}:
            self._advance()
            self._advance()
            self._consume_digits(self._is_hex_digit)
            if self._peek() == ".":
                token_type = TokenType.FLOAT
                self._advance()
                self._consume_digits(self._is_hex_digit)
            if self._peek() in {"p", "P"}:
                token_type = TokenType.FLOAT
                self._advance()
                self._consume_sign()
                self._require_digit("hexadecimal floating exponent")
                self._consume_digits(str.isdigit)
        else:
            self._consume_digits(str.isdigit)
            if self._peek() == ".":
                token_type = TokenType.FLOAT
                self._advance()
                self._consume_digits(str.isdigit)
            if self._peek() in {"e", "E"}:
                token_type = TokenType.FLOAT
                self._advance()
                self._consume_sign()
                self._require_digit("floating exponent")
                self._consume_digits(str.isdigit)

        suffix_chars = FLOAT_SUFFIX_CHARS if token_type == TokenType.FLOAT else INTEGER_SUFFIX_CHARS
        while self._peek() in suffix_chars:
            self._advance()

        self._line_has_code = True
        return self._token_from(token_type, start_line, start_column, start_index)

    def _read_string(self) -> Token:
        return self._read_quoted(TokenType.STRING, '"')

    def _read_char(self) -> Token:
        return self._read_quoted(TokenType.CHAR, "'")

    def _read_prefixed_quoted(self) -> Token:
        if self.source.startswith("u8", self.index):
            prefix_length = 2
        else:
            prefix_length = 1

        quote = self._peek(prefix_length)
        token_type = TokenType.STRING if quote == '"' else TokenType.CHAR
        return self._read_quoted(token_type, quote, prefix_length=prefix_length)

    def _read_quoted(self, token_type: TokenType, quote: str, *, prefix_length: int = 0) -> Token:
        start_line, start_column, start_index = self.line, self.column, self.index
        for _ in range(prefix_length):
            self._advance()
        self._advance()

        while not self._at_end and self._peek() != quote:
            if self._peek() == "\n":
                raise LexerError("Unterminated literal", start_line, start_column)
            if self._peek() == "\\":
                self._advance()
                if self._at_end:
                    raise LexerError("Unterminated escape sequence", start_line, start_column)
            self._advance()

        if self._at_end:
            raise LexerError("Unterminated literal", start_line, start_column)

        self._advance()
        self._line_has_code = True
        lexeme = self.source[start_index : self.index]
        literal = lexeme[prefix_length + 1 : -1]
        return Token(token_type, lexeme, start_line, start_column, start_index, literal)

    def _read_comment(self) -> Token:
        start_line, start_column, start_index = self.line, self.column, self.index
        self._advance()

        if self._match("/"):
            while not self._at_end and self._peek() != "\n":
                self._advance()
            return self._token_from(TokenType.COMMENT, start_line, start_column, start_index)

        self._match("*")
        while not self._at_end:
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                return self._token_from(TokenType.COMMENT, start_line, start_column, start_index)
            self._advance()

        raise LexerError("Unterminated block comment", start_line, start_column)

    def _read_preprocessor(self) -> Token:
        start_line, start_column, start_index = self.line, self.column, self.index

        while not self._at_end:
            if self._peek() == "\\" and self._peek_next() == "\n":
                self._advance()
                self._advance()
                continue
            if self._peek() == "\n":
                break
            self._advance()

        self._line_has_code = True
        return self._token_from(TokenType.PREPROCESSOR, start_line, start_column, start_index)

    def _read_operator_or_punctuator(self) -> Token:
        start_line, start_column, start_index = self.line, self.column, self.index

        for operator in OPERATORS:
            if self.source.startswith(operator, self.index):
                for _ in operator:
                    self._advance()
                self._line_has_code = True
                return Token(TokenType.OPERATOR, operator, start_line, start_column, start_index)

        char = self._peek()
        if char in PUNCTUATORS:
            self._advance()
            self._line_has_code = True
            return Token(TokenType.PUNCTUATOR, char, start_line, start_column, start_index)

        raise LexerError(f"Unexpected character {char!r}", start_line, start_column)

    def _consume_digits(self, predicate) -> None:
        while not self._at_end and predicate(self._peek()):
            self._advance()

    def _consume_sign(self) -> None:
        if self._peek() in {"+", "-"}:
            self._advance()

    def _require_digit(self, context: str) -> None:
        if not self._peek().isdigit():
            raise LexerError(f"Expected digit in {context}", self.line, self.column)

    @staticmethod
    def _is_identifier_start(char: str) -> bool:
        return char == "_" or char.isalpha()

    @staticmethod
    def _is_identifier_part(char: str) -> bool:
        return char == "_" or char.isalnum()

    @staticmethod
    def _is_hex_digit(char: str) -> bool:
        return char.isdigit() or char.lower() in {"a", "b", "c", "d", "e", "f"}

    def _starts_prefixed_literal(self) -> bool:
        if self.source.startswith("u8", self.index):
            return self._peek(2) == '"'
        if self._peek() in {"L", "u", "U"}:
            return self._peek_next() in {'"', "'"}
        return False


def tokenize(source: str, *, keep_comments: bool = False, add_eof: bool = True) -> list[Token]:
    return LexicalAnalyzer(source, keep_comments=keep_comments, add_eof=add_eof).tokenize()


def iter_tokens(source: str, *, keep_comments: bool = False, add_eof: bool = False) -> Iterable[Token]:
    return LexicalAnalyzer(source, keep_comments=keep_comments, add_eof=add_eof).iter_tokens()


def tokenize_file(path: str | Path, *, keep_comments: bool = False, add_eof: bool = True, encoding: str = "utf-8") -> list[Token]:
    source = Path(path).read_text(encoding=encoding)
    return tokenize(source, keep_comments=keep_comments, add_eof=add_eof)
