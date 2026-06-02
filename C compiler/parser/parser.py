from __future__ import annotations

from lexer import SourcePosition, Token, TokenType, tokenize

from .ast import (
    BinaryExpression,
    BreakStatement,
    CallExpression,
    CompoundStatement,
    ContinueStatement,
    Declaration,
    Expression,
    ExpressionStatement,
    ForStatement,
    FunctionDefinition,
    Identifier,
    IfStatement,
    InitializerList,
    ArrayAccess,
    Literal,
    Parameter,
    Program,
    ReturnStatement,
    Statement,
    UnaryExpression,
    WhileStatement,
)


TYPE_KEYWORDS = {
    "char",
    "const",
    "double",
    "float",
    "int",
    "long",
    "short",
    "signed",
    "static",
    "unsigned",
    "void",
}

PREFIX_OPERATORS = {"+", "-", "!", "~", "*", "&", "++", "--", "sizeof"}
POSTFIX_OPERATORS = {"++", "--"}
ASSIGNMENT_OPERATORS = {"=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "^=", "|="}
PRECEDENCE = {
    "||": 1,
    "&&": 2,
    "|": 3,
    "^": 4,
    "&": 5,
    "==": 6,
    "!=": 6,
    "<": 7,
    "<=": 7,
    ">": 7,
    ">=": 7,
    "<<": 8,
    ">>": 8,
    "+": 9,
    "-": 9,
    "*": 10,
    "/": 10,
    "%": 10,
}


class ParserError(SyntaxError):
    def __init__(self, message: str, token: Token) -> None:
        super().__init__(f"{message} at line {token.line}, column {token.column}")
        self.message = message
        self.token = token


class CParser:
    """Recursive-descent parser for a practical C subset."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = [token for token in tokens if token.type not in {TokenType.COMMENT, TokenType.PREPROCESSOR}]
        self.current = 0

    def parse(self) -> Program:
        declarations = []
        start = self._peek().position

        while not self._is_at_end:
            declarations.append(self._external_declaration())

        return Program(start, declarations)

    @property
    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _external_declaration(self) -> Declaration | FunctionDefinition:
        position = self._peek().position
        type_specifier = self._type_specifier()
        name = self._consume(TokenType.IDENTIFIER, "Expected declaration name").lexeme
        array_size = self._array_size()

        if self._match_lexeme("("):
            parameters = self._parameters()
            self._consume_lexeme(")", "Expected ')' after parameters")
            if self._check_lexeme("{"):
                body = self._compound_statement()
                return FunctionDefinition(position, type_specifier, name, parameters, body)
            self._consume_lexeme(";", "Expected ';' after function declaration")
            return Declaration(position, f"{type_specifier} function", name)

        initializer = None
        if self._match_lexeme("="):
            initializer = self._initializer()
        self._consume_lexeme(";", "Expected ';' after declaration")
        return Declaration(position, type_specifier, name, initializer, array_size)

    def _parameters(self) -> list[Parameter]:
        parameters: list[Parameter] = []
        if self._check_lexeme(")"):
            return parameters
        if self._check_keyword("void") and self._peek_next().lexeme == ")":
            self._advance()
            return parameters

        while True:
            position = self._peek().position
            type_specifier = self._type_specifier()
            name = None
            if self._check(TokenType.IDENTIFIER):
                name = self._advance().lexeme
            parameters.append(Parameter(position, type_specifier, name))
            if not self._match_lexeme(","):
                break
        return parameters

    def _type_specifier(self) -> str:
        parts = []
        while self._check(TokenType.KEYWORD) and self._peek().lexeme in TYPE_KEYWORDS:
            parts.append(self._advance().lexeme)
        if not parts:
            raise ParserError("Expected type specifier", self._peek())
        while self._match_lexeme("*"):
            parts.append("*")
        return " ".join(parts).replace(" *", "*")

    def _compound_statement(self) -> CompoundStatement:
        start = self._consume_lexeme("{", "Expected '{' to start compound statement").position
        items: list[Statement | Declaration] = []

        while not self._check_lexeme("}") and not self._is_at_end:
            if self._starts_declaration():
                items.append(self._local_declaration())
            else:
                items.append(self._statement())

        self._consume_lexeme("}", "Expected '}' after compound statement")
        return CompoundStatement(start, items)

    def _local_declaration(self) -> Declaration:
        position = self._peek().position
        type_specifier = self._type_specifier()
        name = self._consume(TokenType.IDENTIFIER, "Expected variable name").lexeme
        array_size = self._array_size()
        initializer = None
        if self._match_lexeme("="):
            initializer = self._initializer()
        self._consume_lexeme(";", "Expected ';' after declaration")
        return Declaration(position, type_specifier, name, initializer, array_size)

    def _array_size(self) -> Expression | None:
        if not self._match_lexeme("["):
            return None
        size = None if self._check_lexeme("]") else self._expression()
        self._consume_lexeme("]", "Expected ']' after array size")
        return size

    def _initializer(self) -> Expression:
        if self._match_lexeme("{"):
            position = self._previous().position
            values = []
            if not self._check_lexeme("}"):
                while True:
                    values.append(self._initializer())
                    if not self._match_lexeme(","):
                        break
                    if self._check_lexeme("}"):
                        break
            self._consume_lexeme("}", "Expected '}' after initializer list")
            return InitializerList(position, values)
        return self._expression()

    def _statement(self) -> Statement:
        if self._check_lexeme("{"):
            return self._compound_statement()
        if self._match_keyword("return"):
            return self._return_statement()
        if self._match_keyword("if"):
            return self._if_statement()
        if self._match_keyword("while"):
            return self._while_statement()
        if self._match_keyword("for"):
            return self._for_statement()
        if self._match_keyword("break"):
            position = self._previous().position
            self._consume_lexeme(";", "Expected ';' after break")
            return BreakStatement(position)
        if self._match_keyword("continue"):
            position = self._previous().position
            self._consume_lexeme(";", "Expected ';' after continue")
            return ContinueStatement(position)
        return self._expression_statement()

    def _return_statement(self) -> ReturnStatement:
        position = self._previous().position
        value = None if self._check_lexeme(";") else self._expression()
        self._consume_lexeme(";", "Expected ';' after return statement")
        return ReturnStatement(position, value)

    def _if_statement(self) -> IfStatement:
        position = self._previous().position
        self._consume_lexeme("(", "Expected '(' after if")
        condition = self._expression()
        self._consume_lexeme(")", "Expected ')' after if condition")
        then_branch = self._statement()
        else_branch = self._statement() if self._match_keyword("else") else None
        return IfStatement(position, condition, then_branch, else_branch)

    def _while_statement(self) -> WhileStatement:
        position = self._previous().position
        self._consume_lexeme("(", "Expected '(' after while")
        condition = self._expression()
        self._consume_lexeme(")", "Expected ')' after while condition")
        return WhileStatement(position, condition, self._statement())

    def _for_statement(self) -> ForStatement:
        position = self._previous().position
        self._consume_lexeme("(", "Expected '(' after for")

        if self._match_lexeme(";"):
            initializer = None
        elif self._starts_declaration():
            initializer = self._local_declaration()
        else:
            initializer = self._expression()
            self._consume_lexeme(";", "Expected ';' after for initializer")

        condition = None if self._check_lexeme(";") else self._expression()
        self._consume_lexeme(";", "Expected ';' after for condition")
        increment = None if self._check_lexeme(")") else self._expression()
        self._consume_lexeme(")", "Expected ')' after for clauses")
        return ForStatement(position, initializer, condition, increment, self._statement())

    def _expression_statement(self) -> ExpressionStatement:
        position = self._peek().position
        expression = None if self._check_lexeme(";") else self._expression()
        self._consume_lexeme(";", "Expected ';' after expression")
        return ExpressionStatement(position, expression)

    def _expression(self) -> Expression:
        return self._assignment()

    def _assignment(self) -> Expression:
        expression = self._binary_expression()
        if self._peek().lexeme in ASSIGNMENT_OPERATORS:
            operator = self._advance()
            right = self._assignment()
            return BinaryExpression(operator.position, operator.lexeme, expression, right)
        return expression

    def _binary_expression(self, min_precedence: int = 1) -> Expression:
        left = self._unary()

        while self._peek().lexeme in PRECEDENCE and PRECEDENCE[self._peek().lexeme] >= min_precedence:
            operator = self._advance()
            precedence = PRECEDENCE[operator.lexeme]
            right = self._binary_expression(precedence + 1)
            left = BinaryExpression(operator.position, operator.lexeme, left, right)

        return left

    def _unary(self) -> Expression:
        if self._peek().lexeme in PREFIX_OPERATORS:
            operator = self._advance()
            return UnaryExpression(operator.position, operator.lexeme, self._unary())
        return self._postfix()

    def _postfix(self) -> Expression:
        expression = self._primary()

        while True:
            if self._match_lexeme("("):
                arguments = []
                if not self._check_lexeme(")"):
                    while True:
                        arguments.append(self._expression())
                        if not self._match_lexeme(","):
                            break
                close = self._consume_lexeme(")", "Expected ')' after call arguments")
                expression = CallExpression(close.position, expression, arguments)
            elif self._match_lexeme("["):
                position = self._previous().position
                index = self._expression()
                self._consume_lexeme("]", "Expected ']' after array index")
                expression = ArrayAccess(position, expression, index)
            elif self._peek().lexeme in POSTFIX_OPERATORS:
                operator = self._advance()
                expression = UnaryExpression(operator.position, operator.lexeme, expression, postfix=True)
            else:
                break

        return expression

    def _primary(self) -> Expression:
        token = self._advance()
        if token.type == TokenType.IDENTIFIER:
            return Identifier(token.position, token.lexeme)
        if token.type in {TokenType.INTEGER, TokenType.FLOAT, TokenType.STRING, TokenType.CHAR}:
            return Literal(token.position, token.literal if token.literal is not None else token.lexeme, token.lexeme)
        if token.lexeme == "(":
            expression = self._expression()
            self._consume_lexeme(")", "Expected ')' after expression")
            return expression
        raise ParserError("Expected expression", token)

    def _starts_declaration(self) -> bool:
        return self._check(TokenType.KEYWORD) and self._peek().lexeme in TYPE_KEYWORDS

    def _match_keyword(self, lexeme: str) -> bool:
        if self._check_keyword(lexeme):
            self._advance()
            return True
        return False

    def _check_keyword(self, lexeme: str) -> bool:
        return self._check(TokenType.KEYWORD) and self._peek().lexeme == lexeme

    def _match_lexeme(self, lexeme: str) -> bool:
        if self._check_lexeme(lexeme):
            self._advance()
            return True
        return False

    def _check_lexeme(self, lexeme: str) -> bool:
        return not self._is_at_end and self._peek().lexeme == lexeme

    def _consume_lexeme(self, lexeme: str, message: str) -> Token:
        if self._check_lexeme(lexeme):
            return self._advance()
        raise ParserError(message, self._peek())

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise ParserError(message, self._peek())

    def _check(self, token_type: TokenType) -> bool:
        return not self._is_at_end and self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end:
            self.current += 1
        return self._previous()

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _peek_next(self) -> Token:
        if self.current + 1 >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[self.current + 1]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]


def parse_tokens(tokens: list[Token]) -> Program:
    return CParser(tokens).parse()


def parse(source: str) -> Program:
    return parse_tokens(tokenize(source))
