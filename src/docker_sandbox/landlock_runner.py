"""Run Sandbox Agent after applying a Linux Landlock path policy."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SYS_LANDLOCK_CREATE_RULESET = 444
_SYS_LANDLOCK_ADD_RULE = 445
_SYS_LANDLOCK_RESTRICT_SELF = 446
_LANDLOCK_CREATE_RULESET_VERSION = 1
_LANDLOCK_RULE_PATH_BENEATH = 1
_PR_SET_NO_NEW_PRIVS = 38
_O_PATH = getattr(os, "O_PATH", 0o10000000)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0o2000000)

_ACCESS_FS_EXECUTE = 1 << 0
_ACCESS_FS_WRITE_FILE = 1 << 1
_ACCESS_FS_READ_FILE = 1 << 2
_ACCESS_FS_READ_DIR = 1 << 3
_ACCESS_FS_REMOVE_DIR = 1 << 4
_ACCESS_FS_REMOVE_FILE = 1 << 5
_ACCESS_FS_MAKE_CHAR = 1 << 6
_ACCESS_FS_MAKE_DIR = 1 << 7
_ACCESS_FS_MAKE_REG = 1 << 8
_ACCESS_FS_MAKE_SOCK = 1 << 9
_ACCESS_FS_MAKE_FIFO = 1 << 10
_ACCESS_FS_MAKE_BLOCK = 1 << 11
_ACCESS_FS_MAKE_SYM = 1 << 12
_ACCESS_FS_REFER = 1 << 13
_ACCESS_FS_TRUNCATE = 1 << 14

_READ_RIGHTS = _ACCESS_FS_READ_FILE | _ACCESS_FS_READ_DIR
_EXECUTE_RIGHTS = _ACCESS_FS_EXECUTE
_WRITE_RIGHTS = (
    _ACCESS_FS_WRITE_FILE
    | _ACCESS_FS_REMOVE_DIR
    | _ACCESS_FS_REMOVE_FILE
    | _ACCESS_FS_MAKE_CHAR
    | _ACCESS_FS_MAKE_DIR
    | _ACCESS_FS_MAKE_REG
    | _ACCESS_FS_MAKE_SOCK
    | _ACCESS_FS_MAKE_FIFO
    | _ACCESS_FS_MAKE_BLOCK
    | _ACCESS_FS_MAKE_SYM
)

_ACCESS_BY_NAME = {
    "r": _READ_RIGHTS,
    "w": _WRITE_RIGHTS,
    "x": _EXECUTE_RIGHTS,
}
_LANDLOCK_BOOTSTRAP_CTYPES_ENVIRONMENT_VARIABLE = (
    "SANDBOX_ALLOW_LANDLOCK_BOOTSTRAP_CTYPES"
)


class _LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
    ]


class _LandlockPathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


@dataclass(frozen=True)
class _PathRule:
    path: Path
    access: str


def main(arguments: list[str] | None = None) -> int:
    """Apply Landlock, then run the selected sandbox workload."""
    parsed_arguments = _parse_arguments(arguments)
    rules = _read_policy(parsed_arguments.policy)
    _apply_landlock_rules(rules)
    _drop_bootstrap_ctypes_modules()

    if parsed_arguments.target == "sandbox_tester":
        sandbox_tester_main = _import_sandbox_tester_main()

        _disable_runtime_ctypes_access()

        sandbox_arguments = ["--config", str(parsed_arguments.config)]
        if parsed_arguments.verbose:
            sandbox_arguments.append("--verbose")
        if parsed_arguments.serialize_evidence:
            sandbox_arguments.append("--serialize-evidence")
        return sandbox_tester_main(sandbox_arguments)

    _disable_runtime_ctypes_access()

    from sandbox_agent.cli import main as sandbox_agent_main

    return sandbox_agent_main([])


def _import_sandbox_tester_main() -> Callable[[list[str] | None], int]:
    os.environ[_LANDLOCK_BOOTSTRAP_CTYPES_ENVIRONMENT_VARIABLE] = "1"
    try:
        from sandbox_tester.cli import main as sandbox_tester_main
    finally:
        os.environ.pop(_LANDLOCK_BOOTSTRAP_CTYPES_ENVIRONMENT_VARIABLE, None)

    return sandbox_tester_main


def _drop_bootstrap_ctypes_modules() -> None:
    globals().pop("ctypes", None)
    sys.modules.pop("ctypes", None)
    sys.modules.pop("_ctypes", None)


def _disable_runtime_ctypes_access() -> None:
    ctypes_module = sys.modules.get("ctypes")
    if ctypes_module is None:
        return

    denied_loader = _build_denied_ctypes_loader()
    for name in ("CDLL", "PyDLL", "WinDLL", "OleDLL"):
        if hasattr(ctypes_module, name):
            setattr(ctypes_module, name, denied_loader)

    denied_library = _DeniedCtypesLibrary()
    for name in ("cdll", "pydll", "windll", "oledll"):
        if hasattr(ctypes_module, name):
            setattr(ctypes_module, name, denied_library)


class _DeniedCtypesLibrary:
    def __getattr__(self, name: str) -> object:
        raise ModuleNotFoundError("'ctypes' is denied by sandbox profile")


def _build_denied_ctypes_loader() -> object:
    def _denied_ctypes_loader(*args: object, **kwargs: object) -> object:
        raise ModuleNotFoundError("'ctypes' is denied by sandbox profile")

    return _denied_ctypes_loader


def _parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Sandbox Agent under a Landlock path policy."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument(
        "--target",
        choices=("sandbox_agent", "sandbox_tester"),
        default="sandbox_agent",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--serialize-evidence", action="store_true")
    return parser.parse_args(arguments)


def _read_policy(path: Path) -> list[_PathRule]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("Landlock policy must contain a list named 'rules'.")

    return [_path_rule_from_json(rule) for rule in rules]


def _path_rule_from_json(data: Any) -> _PathRule:
    if not isinstance(data, dict):
        raise ValueError("Landlock path rule must be an object.")

    path = data.get("path")
    access = data.get("access")
    if not isinstance(path, str) or not isinstance(access, str):
        raise ValueError("Landlock path rule requires string path and access values.")

    return _PathRule(path=Path(path), access=access)


def _apply_landlock_rules(rules: list[_PathRule]) -> None:
    abi_version = _get_landlock_abi_version()
    handled_access = _supported_access_mask(abi_version)
    ruleset_fd = _create_ruleset(handled_access)

    try:
        for rule in rules:
            _add_path_rule(ruleset_fd, rule, handled_access)

        _set_no_new_privileges()
        _restrict_self(ruleset_fd)
    finally:
        os.close(ruleset_fd)


def _get_landlock_abi_version() -> int:
    abi_version = _syscall(
        _SYS_LANDLOCK_CREATE_RULESET,
        None,
        0,
        _LANDLOCK_CREATE_RULESET_VERSION,
    )
    return int(abi_version)


def _supported_access_mask(abi_version: int) -> int:
    access = _READ_RIGHTS | _EXECUTE_RIGHTS | _WRITE_RIGHTS
    if abi_version >= 2:
        access |= _ACCESS_FS_REFER
    if abi_version >= 3:
        access |= _ACCESS_FS_TRUNCATE
    return access


def _create_ruleset(handled_access: int) -> int:
    attr = _LandlockRulesetAttr(handled_access_fs=handled_access)
    return int(
        _syscall(
            _SYS_LANDLOCK_CREATE_RULESET,
            ctypes.byref(attr),
            ctypes.sizeof(attr),
            0,
        )
    )


def _add_path_rule(
    ruleset_fd: int,
    rule: _PathRule,
    handled_access: int,
) -> None:
    allowed_access = _parse_access(rule.access) & handled_access
    parent_fd = os.open(rule.path, _O_PATH | _O_CLOEXEC)
    try:
        attr = _LandlockPathBeneathAttr(
            allowed_access=allowed_access,
            parent_fd=parent_fd,
        )
        _syscall(
            _SYS_LANDLOCK_ADD_RULE,
            ruleset_fd,
            _LANDLOCK_RULE_PATH_BENEATH,
            ctypes.byref(attr),
            0,
        )
    finally:
        os.close(parent_fd)


def _parse_access(access: str) -> int:
    rights = 0
    for name in access:
        try:
            rights |= _ACCESS_BY_NAME[name]
        except KeyError as error:
            raise ValueError(f"Unknown Landlock access right: {name}") from error

    rights |= _ACCESS_FS_REFER | _ACCESS_FS_TRUNCATE
    return rights


def _set_no_new_privileges() -> None:
    _prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)


def _restrict_self(ruleset_fd: int) -> None:
    _syscall(_SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0)


def _syscall(number: int, *arguments: object) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(number, *arguments)
    if result < 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))
    return int(result)


def _prctl(option: int, arg2: int, arg3: int, arg4: int, arg5: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.prctl(option, arg2, arg3, arg4, arg5)
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


if __name__ == "__main__":
    raise SystemExit(main())
