# C Compiler Frontend

This project is a Python-based frontend for a small C compiler. It reads C source code, runs it through separate compiler phases, and generates a JSON parse tree.

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
cd "C:\Users\Gaurav\Desktop\Compiler"
```
```powershell
Run the compiler on specific input file  `main.c` => Give input file by `python main.py ./C source file path`

