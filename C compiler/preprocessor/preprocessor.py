from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Macro:
    name: str
    replacement: str
    line: int


@dataclass(frozen=True)
class PreprocessResult:
    source: str
    includes: list[str] = field(default_factory=list)
    macros: dict[str, Macro] = field(default_factory=dict)


def preprocess_source(source: str) -> PreprocessResult:
    processor = _Preprocessor()
    return processor.process_source(source)


def preprocess_file(path: str | Path, *, encoding: str = "utf-8") -> PreprocessResult:
    processor = _Preprocessor(encoding=encoding)
    return processor.process_file(Path(path))


class _Preprocessor:
    def __init__(self, *, encoding: str = "utf-8") -> None:
        self.encoding = encoding
        self.includes: list[str] = []
        self.macros: dict[str, Macro] = {}
        self.included_files: set[Path] = set()

    def process_source(self, source: str, *, base_dir: Path | None = None) -> PreprocessResult:
        output = self._process_lines(source.splitlines(), base_dir=base_dir)
        return PreprocessResult("\n".join(output), list(self.includes), dict(self.macros))

    def process_file(self, path: Path) -> PreprocessResult:
        full_path = path.resolve()
        source = full_path.read_text(encoding=self.encoding)
        return self.process_source(source, base_dir=full_path.parent)

    def _process_lines(self, lines: list[str], *, base_dir: Path | None) -> list[str]:
        output_lines: list[str] = []

        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#include"):
                include = _read_include(stripped)
                self.includes.append(include.name)
                if include.is_local and base_dir is not None:
                    output_lines.extend(self._process_local_include(include.name, base_dir))
                else:
                    output_lines.append("")
                continue
            if stripped.startswith("#define"):
                macro = _read_macro(stripped, line_number)
                if macro is not None:
                    self.macros[macro.name] = macro
                output_lines.append("")
                continue
            output_lines.append(_expand_macros(line, self.macros))

        return output_lines

    def _process_local_include(self, include_name: str, base_dir: Path) -> list[str]:
        include_path = (base_dir / include_name).resolve()
        if include_path in self.included_files:
            return [""]
        self.included_files.add(include_path)
        try:
            source = include_path.read_text(encoding=self.encoding)
        except OSError:
            return [""]
        return self._process_lines(source.splitlines(), base_dir=include_path.parent)


@dataclass(frozen=True)
class _Include:
    name: str
    is_local: bool


def _read_include_name(line: str) -> str:
    return _read_include(line).name


def _read_include(line: str) -> _Include:
    value = line.removeprefix("#include").strip()
    if value.startswith("<") and value.endswith(">"):
        return _Include(value[1:-1], False)
    if value.startswith('"') and value.endswith('"'):
        return _Include(value[1:-1], True)
    return _Include(value, False)


def _read_macro(line: str, line_number: int) -> Macro | None:
    rest = line.removeprefix("#define").strip()
    if not rest:
        return None

    parts = rest.split(maxsplit=1)
    name = parts[0]
    if "(" in name:
        return None

    replacement = parts[1] if len(parts) > 1 else "1"
    return Macro(name, replacement, line_number)


def _expand_macros(line: str, macros: dict[str, Macro]) -> str:
    result: list[str] = []
    index = 0

    while index < len(line):
        char = line[index]
        if char in {'"', "'"}:
            literal, index = _consume_literal(line, index)
            result.append(literal)
            continue
        if char == "/" and index + 1 < len(line) and line[index + 1] == "/":
            result.append(line[index:])
            break
        if _is_identifier_start(char):
            start = index
            index += 1
            while index < len(line) and _is_identifier_part(line[index]):
                index += 1
            name = line[start:index]
            result.append(macros[name].replacement if name in macros else name)
            continue

        result.append(char)
        index += 1

    return "".join(result)


def _consume_literal(line: str, start: int) -> tuple[str, int]:
    quote = line[start]
    index = start + 1

    while index < len(line):
        if line[index] == "\\":
            index += 2
            continue
        if line[index] == quote:
            index += 1
            break
        index += 1

    return line[start:index], index


def _is_identifier_start(char: str) -> bool:
    return char == "_" or char.isalpha()


def _is_identifier_part(char: str) -> bool:
    return char == "_" or char.isalnum()
