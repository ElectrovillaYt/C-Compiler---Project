from __future__ import annotations

import json
from dataclasses import dataclass, fields
from typing import Any

from lexer import SourcePosition
from parser import (
    ASTNode,
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
    Program,
    ReturnStatement,
    UnaryExpression,
    WhileStatement,
)


STANDARD_FUNCTIONS: dict[str, dict[str, Any]] = {
    "printf": {"return_type": "int", "parameters": [{"name": "format", "type": "const char*"}]},
    "scanf": {"return_type": "int", "parameters": [{"name": "format", "type": "const char*"}]},
    "puts": {"return_type": "int", "parameters": [{"name": "s", "type": "const char*"}]},
    "gets": {"return_type": "char*", "parameters": [{"name": "s", "type": "char*"}]},
    "putchar": {"return_type": "int", "parameters": [{"name": "c", "type": "int"}]},
    "getchar": {"return_type": "int", "parameters": []},
}


class SemanticError(Exception):
    def __init__(self, message: str, position: SourcePosition) -> None:
        super().__init__(f"{message} at line {position.line}, column {position.column}")
        self.message = message
        self.position = position


@dataclass(frozen=True)
class SemanticResult:
    parse_tree: dict[str, Any]
    symbols: dict[str, Any]

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.parse_tree, indent=indent)


class SemanticAnalyzer:
    """Builds a JSON-ready parse tree"""

    def __init__(self) -> None:
        self.scopes: list[dict[str, str]] = [{}]
        self.functions: dict[str, dict[str, Any]] = dict(STANDARD_FUNCTIONS)
        self.loop_depth = 0
        self.current_function_return_type: str | None = None

    def analyze(self, program: Program) -> SemanticResult:
        for declaration in program.declarations:
            if isinstance(declaration, FunctionDefinition):
                self._declare_function(declaration)
            elif isinstance(declaration, Declaration):
                self._declare_variable(declaration)

        for declaration in program.declarations:
            if isinstance(declaration, FunctionDefinition):
                self._analyze_function(declaration)
            elif isinstance(declaration, Declaration) and declaration.initializer is not None:
                self._analyze_expression(declaration.initializer)

        return SemanticResult(
            parse_tree=self._node_to_dict(program),
            symbols={"globals": dict(self.scopes[0]), "functions": self.functions},
        )

    def _declare_function(self, function: FunctionDefinition) -> None:
        if function.name in self.functions or function.name in self.scopes[0]:
            raise SemanticError(f"Duplicate global symbol '{function.name}'", function.position)
        self.functions[function.name] = {
            "return_type": function.return_type,
            "parameters": [
                {"name": parameter.name, "type": parameter.type_specifier}
                for parameter in function.parameters
            ],
        }

    def _analyze_function(self, function: FunctionDefinition) -> None:
        previous_return_type = self.current_function_return_type
        self.current_function_return_type = function.return_type
        self._push_scope()
        for parameter in function.parameters:
            if parameter.name is not None:
                self._declare_name(parameter.name, parameter.type_specifier, parameter.position)
        self._analyze_compound(function.body, create_scope=False)
        self._pop_scope()
        self.current_function_return_type = previous_return_type

    def _analyze_compound(self, compound: CompoundStatement, *, create_scope: bool = True) -> None:
        if create_scope:
            self._push_scope()
        for item in compound.items:
            if isinstance(item, Declaration):
                self._declare_variable(item)
                if item.initializer is not None:
                    self._analyze_expression(item.initializer)
            else:
                self._analyze_statement(item)
        if create_scope:
            self._pop_scope()

    def _analyze_statement(self, statement) -> None:
        if isinstance(statement, CompoundStatement):
            self._analyze_compound(statement)
        elif isinstance(statement, ReturnStatement):
            if self.current_function_return_type is None:
                raise SemanticError("Return statement outside function", statement.position)
            if self.current_function_return_type == "void" and statement.value is not None:
                raise SemanticError("Void function cannot return a value", statement.position)
            if self.current_function_return_type != "void" and statement.value is None:
                raise SemanticError("Non-void function must return a value", statement.position)
            if statement.value is not None:
                self._analyze_expression(statement.value)
        elif isinstance(statement, IfStatement):
            self._analyze_expression(statement.condition)
            self._analyze_statement(statement.then_branch)
            if statement.else_branch is not None:
                self._analyze_statement(statement.else_branch)
        elif isinstance(statement, WhileStatement):
            self._analyze_expression(statement.condition)
            self.loop_depth += 1
            self._analyze_statement(statement.body)
            self.loop_depth -= 1
        elif isinstance(statement, ForStatement):
            self._push_scope()
            if isinstance(statement.initializer, Declaration):
                self._declare_variable(statement.initializer)
                if statement.initializer.initializer is not None:
                    self._analyze_expression(statement.initializer.initializer)
            elif statement.initializer is not None:
                self._analyze_expression(statement.initializer)
            if statement.condition is not None:
                self._analyze_expression(statement.condition)
            if statement.increment is not None:
                self._analyze_expression(statement.increment)
            self.loop_depth += 1
            self._analyze_statement(statement.body)
            self.loop_depth -= 1
            self._pop_scope()
        elif isinstance(statement, BreakStatement | ContinueStatement):
            if self.loop_depth == 0:
                keyword = "break" if isinstance(statement, BreakStatement) else "continue"
                raise SemanticError(f"'{keyword}' used outside loop", statement.position)
        elif isinstance(statement, ExpressionStatement):
            if statement.expression is not None:
                self._analyze_expression(statement.expression)

    def _analyze_expression(self, expression: Expression) -> None:
        if isinstance(expression, Identifier):
            if not self._resolve(expression.name) and expression.name not in self.functions:
                raise SemanticError(f"Use of undeclared identifier '{expression.name}'", expression.position)
        elif isinstance(expression, BinaryExpression):
            self._analyze_expression(expression.left)
            self._analyze_expression(expression.right)
        elif isinstance(expression, UnaryExpression):
            self._analyze_expression(expression.operand)
        elif isinstance(expression, CallExpression):
            if isinstance(expression.callee, Identifier) and expression.callee.name not in self.functions:
                raise SemanticError(f"Call to undeclared function '{expression.callee.name}'", expression.position)
            self._analyze_expression(expression.callee)
            for argument in expression.arguments:
                self._analyze_expression(argument)
        elif isinstance(expression, InitializerList):
            for value in expression.values:
                self._analyze_expression(value)
        elif isinstance(expression, ArrayAccess):
            self._analyze_expression(expression.array)
            self._analyze_expression(expression.index)
        elif isinstance(expression, Literal):
            return

    def _declare_variable(self, declaration: Declaration) -> None:
        self._declare_name(declaration.name, declaration.type_specifier, declaration.position)
        if declaration.array_size is not None:
            self._analyze_expression(declaration.array_size)

    def _declare_name(self, name: str, type_specifier: str, position: SourcePosition) -> None:
        if name in self.scopes[-1]:
            raise SemanticError(f"Duplicate declaration of '{name}'", position)
        if name in self.functions and len(self.scopes) == 1:
            raise SemanticError(f"Duplicate global symbol '{name}'", position)
        self.scopes[-1][name] = type_specifier

    def _resolve(self, name: str) -> str | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _push_scope(self) -> None:
        self.scopes.append({})

    def _pop_scope(self) -> None:
        self.scopes.pop()

    def _node_to_dict(self, value: Any) -> Any:
        if isinstance(value, ASTNode):
            data = {"node": type(value).__name__}
            for field in fields(value):
                data[field.name] = self._node_to_dict(getattr(value, field.name))
            return data
        if isinstance(value, SourcePosition):
            return {"line": value.line, "column": value.column, "index": value.index}
        if isinstance(value, list):
            return [self._node_to_dict(item) for item in value]
        if isinstance(value, dict):
            return {key: self._node_to_dict(item) for key, item in value.items()}
        return value


def analyze_semantics(program: Program) -> SemanticResult:
    return SemanticAnalyzer().analyze(program)
