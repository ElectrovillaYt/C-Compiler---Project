from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexer import Token, tokenize
from parser import Program, parse_tokens
from preprocessor import PreprocessResult, preprocess_file, preprocess_source
from semantic import SemanticResult, analyze_semantics


@dataclass(frozen=True)
class FrontendResult:
    source: str
    preprocessed: PreprocessResult
    tokens: list[Token]
    ast: Program
    semantics: SemanticResult


def analyze_source(source: str) -> FrontendResult:
    preprocessed = preprocess_source(source)
    tokens = tokenize(preprocessed.source)
    ast = parse_tokens(tokens)
    semantics = analyze_semantics(ast)
    return FrontendResult(source, preprocessed, tokens, ast, semantics)


def analyze_file(path: str | Path, *, encoding: str = "utf-8") -> FrontendResult:
    source = Path(path).read_text(encoding=encoding)
    preprocessed = preprocess_file(path, encoding=encoding)
    tokens = tokenize(preprocessed.source)
    ast = parse_tokens(tokens)
    semantics = analyze_semantics(ast)
    return FrontendResult(source, preprocessed, tokens, ast, semantics)
