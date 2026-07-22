"""Execute one submitted Python script in a constrained child process."""

from __future__ import annotations

import ast
import builtins
import json
import sys
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

_ALLOWED_MODULE_ROOTS = frozenset(
    {
        "base64",
        "bisect",
        "calendar",
        "cmath",
        "collections",
        "copy",
        "csv",
        "datetime",
        "decimal",
        "difflib",
        "enum",
        "fractions",
        "functools",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "itertools",
        "json",
        "math",
        "operator",
        "random",
        "re",
        "statistics",
        "string",
        "textwrap",
        "time",
        "uuid",
    }
)
_DENIED_BUILTINS = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }
)
_ALLOWED_TOP_LEVEL_NODES = (
    ast.Assign,
    ast.AnnAssign,
    ast.ClassDef,
    ast.Expr,
    ast.FunctionDef,
    ast.Import,
    ast.ImportFrom,
)


def main() -> int:
    """Run a script request from stdin and return the script exit code."""
    request = json.loads(sys.stdin.read())
    script = request.get("script")
    args = request.get("args", [])
    if not isinstance(script, str):
        print("script must be a string", file=sys.stderr)
        return 2
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        print("args must be a list of strings", file=sys.stderr)
        return 2

    try:
        return _run_script(script, args)
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 1


def _run_script(script: str, args: list[str]) -> int:
    tree = ast.parse(script, mode="exec")
    _validate_script_tree(tree)
    globals_namespace = {
        "__builtins__": _safe_builtins(),
        "__name__": "__code_sidecar_script__",
    }
    exec(compile(tree, "<code-sidecar-script>", "exec"), globals_namespace)

    main_function = globals_namespace.get("main")
    if not callable(main_function):
        raise ValueError("script must define callable main(argv)")

    result = main_function(list(args))
    if result is None:
        return 0
    if not isinstance(result, int):
        raise TypeError("main(argv) must return an integer exit code or None")
    if result < 0 or result > 255:
        raise ValueError("main(argv) exit code must be between 0 and 255")
    return result


def _validate_script_tree(tree: ast.Module) -> None:
    has_main = False
    for node in tree.body:
        if not isinstance(node, _ALLOWED_TOP_LEVEL_NODES):
            raise ValueError(
                "top-level code may only contain imports, definitions, and constants"
            )
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            has_main = True
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            _validate_import_node(node)
        if isinstance(node, ast.Expr) and not isinstance(node.value, ast.Constant):
            raise ValueError("top-level expressions must be constants")

    if not has_main:
        raise ValueError("script must define main(argv)")


def _validate_import_node(node: ast.Import | ast.ImportFrom) -> None:
    if isinstance(node, ast.Import):
        module_names = [alias.name for alias in node.names]
    else:
        module_names = [node.module or ""]

    for module_name in module_names:
        root_name = module_name.split(".", 1)[0]
        if root_name not in _ALLOWED_MODULE_ROOTS:
            raise ImportError(f"module is not allowed: {root_name}")


def _safe_builtins() -> Mapping[str, Any]:
    safe_values = {
        name: value
        for name, value in vars(builtins).items()
        if name not in _DENIED_BUILTINS
    }
    safe_values["__import__"] = _allowed_import
    return MappingProxyType(safe_values)


def _allowed_import(
    name: str,
    globals_: dict[str, object] | None = None,
    locals_: dict[str, object] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> object:
    _ = globals_
    _ = locals_
    if level != 0:
        raise ImportError("relative imports are not allowed")

    root_name = name.split(".", 1)[0]
    if root_name not in _ALLOWED_MODULE_ROOTS:
        raise ImportError(f"module is not allowed: {root_name}")
    return builtins.__import__(name, globals_, locals_, fromlist, level)


if __name__ == "__main__":
    raise SystemExit(main())
