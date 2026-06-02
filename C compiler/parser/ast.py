from __future__ import annotations

from dataclasses import dataclass, field

from lexer import SourcePosition


@dataclass(frozen=True)
class ASTNode:
    position: SourcePosition


@dataclass(frozen=True)
class Program(ASTNode):
    declarations: list[ExternalDeclaration] = field(default_factory=list)


@dataclass(frozen=True)
class Parameter(ASTNode):
    type_specifier: str
    name: str | None


@dataclass(frozen=True)
class Declaration(ASTNode):
    type_specifier: str
    name: str
    initializer: Expression | None = None
    array_size: Expression | None = None


@dataclass(frozen=True)
class FunctionDefinition(ASTNode):
    return_type: str
    name: str
    parameters: list[Parameter]
    body: CompoundStatement


ExternalDeclaration = Declaration | FunctionDefinition


@dataclass(frozen=True)
class Statement(ASTNode):
    pass


@dataclass(frozen=True)
class CompoundStatement(Statement):
    items: list[Statement | Declaration] = field(default_factory=list)


@dataclass(frozen=True)
class ReturnStatement(Statement):
    value: Expression | None


@dataclass(frozen=True)
class IfStatement(Statement):
    condition: Expression
    then_branch: Statement
    else_branch: Statement | None = None


@dataclass(frozen=True)
class WhileStatement(Statement):
    condition: Expression
    body: Statement


@dataclass(frozen=True)
class ForStatement(Statement):
    initializer: Declaration | Expression | None
    condition: Expression | None
    increment: Expression | None
    body: Statement


@dataclass(frozen=True)
class BreakStatement(Statement):
    pass


@dataclass(frozen=True)
class ContinueStatement(Statement):
    pass


@dataclass(frozen=True)
class ExpressionStatement(Statement):
    expression: Expression | None


@dataclass(frozen=True)
class Expression(ASTNode):
    pass


@dataclass(frozen=True)
class Identifier(Expression):
    name: str


@dataclass(frozen=True)
class Literal(Expression):
    value: object
    raw: str


@dataclass(frozen=True)
class InitializerList(Expression):
    values: list[Expression] = field(default_factory=list)


@dataclass(frozen=True)
class UnaryExpression(Expression):
    operator: str
    operand: Expression
    postfix: bool = False


@dataclass(frozen=True)
class BinaryExpression(Expression):
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class CallExpression(Expression):
    callee: Expression
    arguments: list[Expression] = field(default_factory=list)


@dataclass(frozen=True)
class ArrayAccess(Expression):
    array: Expression
    index: Expression
