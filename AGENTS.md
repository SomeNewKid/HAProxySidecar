# Agent Instructions

## Python Style

- Follow PEP 8 naming: `snake_case` for functions and variables, `PascalCase` for classes, and `UPPER_CASE` for constants.
- Prefix internal functions, classes, modules, and constants with a single leading underscore.
- Treat functions, classes, modules, and constants without a leading underscore as public project API.
- Public modules, classes, and functions should have concise docstrings.
- Use type hints on function and method signatures.
- Do not require type hints for every local variable.
- Prefer small, explicit functions over clever abstractions.
- Prefer one meaningful operation per line. Avoid nesting function calls when naming
  an intermediate value would make the sequence of work clearer.
- Order modules as: docstring, imports, constants, enums, dataclasses/classes, public functions, then private helper functions.
- Within classes, place fields and class variables first, then `__init__`, then public methods and properties, then private helpers.
- When ordering private helper functions, follow call-flow readability when possible.
- Run `.\scripts\check.ps1` after meaningful code changes.
