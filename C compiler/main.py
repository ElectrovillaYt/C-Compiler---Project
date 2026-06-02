from __future__ import annotations

import json
import sys
from pathlib import Path

from lexer import LexerError, tokenize
from parser import ParserError, parse_tokens
from pipeline import FrontendResult, analyze_file, analyze_source
from preprocessor import preprocess_file, preprocess_source
from semantic import SemanticError, analyze_semantics

__all__ = ["FrontendResult", "analyze_file", "analyze_source", "read_source_from_user", "run_compiler"]

PARSE_TREE_PATH = Path(__file__).resolve().parent / "parseTree.json"


def read_source_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def read_source_from_user() -> str:
    print("Enter C file path, or press Enter to type C code manually:")
    path = input().strip().strip('"')
    if path:
        return read_source_file(path)

    print("Enter C code. Type END on a new line to run the compiler.")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def run_compiler(source: str, *, source_path: str | Path | None = None) -> FrontendResult:
    print("\n[1] Preprocessing")
    preprocessed = preprocess_file(source_path) if source_path is not None else preprocess_source(source)
    print(f"Processed {len(preprocessed.includes)} include(s), {len(preprocessed.macros)} macro(s)")
    if preprocessed.includes:
        print("Includes:", ", ".join(preprocessed.includes))
    if preprocessed.macros:
        macro_summary = ", ".join(f"{name}={macro.replacement}" for name, macro in preprocessed.macros.items())
        print("Macros:", macro_summary)

    print("\n[2] Lexical Analysis")
    tokens = tokenize(preprocessed.source)
    visible_tokens = [token for token in tokens if token.lexeme]
    print(f"Generated {len(visible_tokens)} tokens")
    print("Token preview:", ", ".join(f"{token.type.value}:{token.lexeme}" for token in visible_tokens[:12]))

    print("\n[3] Syntax Analysis")
    ast = parse_tokens(tokens)
    print(f"Parsed {len(ast.declarations)} top-level declaration(s)")

    print("\n[4] Semantic Analysis")
    semantics = analyze_semantics(ast)
    print("Semantic checks passed!")
    PARSE_TREE_PATH.write_text(json.dumps(semantics.parse_tree, indent=2), encoding="utf-8")
    print("Generated parseTree!")
    return FrontendResult(source, preprocessed, tokens, ast, semantics)


def main() -> None:
    try:
        if len(sys.argv) > 1:
            source_path = sys.argv[1]
            source = read_source_file(source_path)
        else:
            source_path = None
            source = read_source_from_user()
    except OSError as error:
        print(f"Could not read C file: {error}")
        return

    if not source.strip():
        print("No C code entered.")
        return

    try:
        run_compiler(source, source_path=source_path)
    except (LexerError, ParserError, SemanticError) as error:
        print("\nCompilation failed")
        print(error)


if __name__ == "__main__":
    main()
