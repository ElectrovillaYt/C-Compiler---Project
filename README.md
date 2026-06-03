# C Compiler Frontend Representation - Semester Project

## This project is a Python-based frontend reprsentation for a small C compiler. Reads C source code, runs it through separate compiler phases, and generates a parse tree in json form for easier representation.

### Has high time-complexity compare to actual compilers amde in Rust or Core C/asm as it is just for semester project representation of complier working overview

The current compiler supports these phases:

```text
C source file
  -> Preprocessing
     -> terminal summary
  -> Lexical Analysis
     -> terminal token count/preview
  -> Syntax Analysis / Parsing
     -> terminal parser summary
  -> Semantic Analysis
  -> Final Output => parseTree.json
```

The compiler code is inside:

```text
C compiler/
```

The input C file is usually:

```text
main.c or any.c source file
```

## How To Run

Open a terminal in the project root:
```powershell
Run the compiler on specific input file  `main.c` => Give input file by `python main.py ./C source file path`

