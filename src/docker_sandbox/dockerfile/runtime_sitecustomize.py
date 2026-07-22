"""Runtime Python restrictions for hardened Docker sandbox images."""

from __future__ import annotations

import importlib.abc
import importlib.util
import inspect
import ipaddress
import os
import pty
import socket
import subprocess
import sys
from pathlib import Path

_DENIED_IMPORT_MODULES = frozenset(
    {
        "_ctypes",
        "ctypes",
        "ensurepip",
        "pip",
        "setuptools",
        "wheel",
    }
)
_DENIED_CODE_ROOTS = tuple(
    Path(path).resolve(strict=False)
    for path in (
        "/sandbox-output",
        "/sandbox-work",
        "/tmp",
    )
)
_DENIED_METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
    }
)
_DENIED_METADATA_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "169.254.0.0/16",
        "fe80::/10",
    )
)
_LANDLOCK_BOOTSTRAP_CTYPES_ENVIRONMENT_VARIABLE = (
    "SANDBOX_ALLOW_LANDLOCK_BOOTSTRAP_CTYPES"
)
_ORIGINAL_SOCKET_CLASS = socket.socket
_ORIGINAL_CREATE_CONNECTION = socket.create_connection
_ORIGINAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location
_ORIGINAL_SUBPROCESS_POPEN = subprocess.Popen
_ORIGINAL_SUBPROCESS_RUN = subprocess.run
_ORIGINAL_PATH_EXISTS = Path.exists
_ORIGINAL_PATH_GLOB = Path.glob
_ORIGINAL_PATH_ITERDIR = Path.iterdir
_DENIED_HARDWARE_COMMAND_MARKERS = frozenset(
    {
        "/dev/snd",
        "/sys/bus/usb",
        "/sys/class/bluetooth",
        "arecord",
        "bluetoothctl",
        "lpstat",
        "lsusb",
        "ttyACM",
        "ttyS",
        "ttyUSB",
        "video*",
        "video4linux2",
    }
)
_ALLOWED_PROCESS_SPAWN_MARKERS = frozenset(
    {
        "/ms-playwright/",
        "/playwright/driver/",
    }
)


class _DeniedModuleFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        module_name = fullname.partition(".")[0]
        if module_name in _DENIED_IMPORT_MODULES:
            if _is_landlock_bootstrap_import(module_name):
                return None

            message = f"{fullname!r} is denied by sandbox profile"
            raise ModuleNotFoundError(message)

        return None


class _DeniedWritableCodeFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        search_paths = path if path is not None else sys.path
        for search_path in search_paths:
            if _path_is_under_denied_code_root(search_path):
                message = (
                    f"Importing {fullname!r} from writable path "
                    f"{search_path!r} is denied by sandbox profile"
                )
                raise ModuleNotFoundError(message)

        return None


def _deny_writable_script_execution() -> None:
    script_path = _get_script_path()
    if script_path is None:
        return

    if not _path_is_under_denied_code_root(script_path):
        return

    os.write(
        2,
        (
            f"Python script execution from writable path {script_path} "
            "is denied by sandbox profile.\n"
        ).encode("utf-8", errors="replace"),
    )
    raise SystemExit(126)


def _deny_writable_spec_from_file_location() -> None:
    def guarded_spec_from_file_location(name, location, *args, **kwargs):  # type: ignore[no-untyped-def]
        if _path_is_under_denied_code_root(location):
            message = (
                f"Importing {name!r} from writable path {location!r} "
                "is denied by sandbox profile"
            )
            raise ModuleNotFoundError(message)

        return _ORIGINAL_SPEC_FROM_FILE_LOCATION(name, location, *args, **kwargs)

    importlib.util.spec_from_file_location = guarded_spec_from_file_location


def _apply_socket_guards() -> None:
    if not _socket_guards_enabled():
        return

    class _GuardedSocket(_ORIGINAL_SOCKET_CLASS):
        def __init__(self, family=-1, type=-1, proto=-1, fileno=None):  # type: ignore[no-untyped-def]
            if _udp_denied() and _is_udp_socket(family, type):
                raise PermissionError("UDP sockets are denied by sandbox profile")

            super().__init__(family, type, proto, fileno)

        def bind(self, address):  # type: ignore[no-untyped-def]
            if _all_interface_bind_denied() and _is_all_interface_bind(address):
                raise PermissionError(
                    "All-interface binds are denied by sandbox profile"
                )

            return super().bind(address)

        def connect(self, address):  # type: ignore[no-untyped-def]
            _raise_if_metadata_address(address)
            return super().connect(address)

        def connect_ex(self, address):  # type: ignore[no-untyped-def]
            _raise_if_metadata_address(address)
            return super().connect_ex(address)

    def guarded_create_connection(address, *args, **kwargs):  # type: ignore[no-untyped-def]
        _raise_if_metadata_address(address)
        return _ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)

    socket.socket = _GuardedSocket
    socket.create_connection = guarded_create_connection


def _socket_guards_enabled() -> bool:
    return _udp_denied() or _all_interface_bind_denied() or _metadata_denied()


def _udp_denied() -> bool:
    return _enabled("SANDBOX_DENY_UDP")


def _all_interface_bind_denied() -> bool:
    return _enabled("SANDBOX_DENY_ALL_INTERFACE_BIND")


def _metadata_denied() -> bool:
    return _enabled("SANDBOX_DENY_METADATA_ENDPOINTS")


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}


def _apply_hardware_device_guards() -> None:
    if not _hardware_device_enumeration_denied():
        return

    def guarded_subprocess_run(args, *run_args, **run_kwargs):  # type: ignore[no-untyped-def]
        if _is_denied_hardware_command(args):
            raise PermissionError(
                "Hardware device enumeration is denied by sandbox profile"
            )

        return _ORIGINAL_SUBPROCESS_RUN(args, *run_args, **run_kwargs)

    def guarded_path_exists(self: Path) -> bool:
        if _is_denied_hardware_path(self):
            raise PermissionError(
                "Hardware device enumeration is denied by sandbox profile"
            )

        return _ORIGINAL_PATH_EXISTS(self)

    def guarded_path_glob(self: Path, pattern: str):  # type: ignore[no-untyped-def]
        if _is_denied_hardware_glob(self, pattern):
            raise PermissionError(
                "Hardware device enumeration is denied by sandbox profile"
            )

        return _ORIGINAL_PATH_GLOB(self, pattern)

    def guarded_path_iterdir(self: Path):  # type: ignore[no-untyped-def]
        if _is_denied_hardware_path(self):
            raise PermissionError(
                "Hardware device enumeration is denied by sandbox profile"
            )

        return _ORIGINAL_PATH_ITERDIR(self)

    subprocess.run = guarded_subprocess_run
    Path.exists = guarded_path_exists  # type: ignore[method-assign]
    Path.glob = guarded_path_glob  # type: ignore[method-assign]
    Path.iterdir = guarded_path_iterdir  # type: ignore[method-assign]


def _apply_process_spawn_guards() -> None:
    if not _process_spawn_denied():
        return

    class GuardedPopen(_ORIGINAL_SUBPROCESS_POPEN):  # type: ignore[misc]
        def __init__(self, args, *popen_args, **popen_kwargs):  # type: ignore[no-untyped-def]
            _raise_if_process_spawn_denied(args)
            super().__init__(args, *popen_args, **popen_kwargs)

    def guarded_run(args, *run_args, **run_kwargs):  # type: ignore[no-untyped-def]
        _raise_if_process_spawn_denied(args)
        return _ORIGINAL_SUBPROCESS_RUN(args, *run_args, **run_kwargs)

    def denied_os_system(command: object) -> int:
        raise PermissionError("Process spawning is denied by sandbox profile")

    def denied_os_popen(command, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise PermissionError("Process spawning is denied by sandbox profile")

    def denied_spawn(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise PermissionError("Process spawning is denied by sandbox profile")

    subprocess.Popen = GuardedPopen
    subprocess.run = guarded_run
    subprocess.call = guarded_run
    subprocess.check_call = guarded_run
    subprocess.check_output = guarded_run
    os.system = denied_os_system
    os.popen = denied_os_popen
    for name in (
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
    ):
        if hasattr(os, name):
            setattr(os, name, denied_spawn)

    if hasattr(pty, "spawn"):
        pty.spawn = denied_spawn  # type: ignore[attr-defined]


def _hardware_device_enumeration_denied() -> bool:
    return _enabled("SANDBOX_DENY_HARDWARE_DEVICE_ENUMERATION")


def _process_spawn_denied() -> bool:
    return _enabled("SANDBOX_DENY_PROCESS_SPAWN")


def _raise_if_process_spawn_denied(args: object) -> None:
    if _is_allowed_process_spawn(args):
        return

    raise PermissionError("Process spawning is denied by sandbox profile")


def _is_allowed_process_spawn(args: object) -> bool:
    text = _command_text(args)
    if not text:
        return False

    normalized_text = text.replace("\\", "/")
    return any(marker in normalized_text for marker in _ALLOWED_PROCESS_SPAWN_MARKERS)


def _is_denied_hardware_command(args: object) -> bool:
    text = _command_text(args)
    if not text:
        return False

    return any(marker in text for marker in _DENIED_HARDWARE_COMMAND_MARKERS)


def _command_text(args: object) -> str:
    if isinstance(args, (str, bytes, os.PathLike)):
        return os.fsdecode(args)

    if not isinstance(args, (list, tuple)):
        return ""

    return " ".join(os.fsdecode(item) for item in args)


def _is_denied_hardware_path(path: object) -> bool:
    path_text = _path_text(path)
    if path_text is None:
        return False

    return path_text in {"/dev/snd", "/sys/bus/usb", "/sys/class/bluetooth"}


def _is_denied_hardware_glob(path: object, pattern: object) -> bool:
    path_text = _path_text(path)
    pattern_text = _path_text(pattern)
    if path_text != "/dev":
        return False

    return pattern_text in {"video*", "ttyS*", "ttyUSB*", "ttyACM*"}


def _path_text(path: object) -> str | None:
    if not isinstance(path, (str, bytes, os.PathLike)):
        return None

    return os.fsdecode(path)


def _is_udp_socket(family: int, socket_type: int) -> bool:
    if socket_type & socket.SOCK_DGRAM != socket.SOCK_DGRAM:
        return False

    return family in {socket.AF_INET, socket.AF_INET6, -1}


def _is_all_interface_bind(address: object) -> bool:
    if not isinstance(address, tuple) or not address:
        return False

    host = address[0]
    return host in {"", "0.0.0.0", "::"}


def _raise_if_metadata_address(address: object) -> None:
    if not _metadata_denied():
        return

    if not isinstance(address, tuple) or not address:
        return

    host = str(address[0]).strip("[]").lower()
    if host in _DENIED_METADATA_HOSTS:
        raise PermissionError("Metadata endpoint access is denied by sandbox profile")

    try:
        ip_address = ipaddress.ip_address(host)
    except ValueError:
        return

    if any(ip_address in network for network in _DENIED_METADATA_NETWORKS):
        raise PermissionError("Metadata endpoint access is denied by sandbox profile")


def _get_script_path() -> Path | None:
    if not sys.argv:
        return None

    script_name = sys.argv[0]
    if not script_name or script_name in {"-c", "-m"}:
        return None

    script_path = Path(script_name)
    if not script_path.is_absolute():
        script_path = Path.cwd() / script_path

    return script_path.resolve(strict=False)


def _path_is_under_denied_code_root(path: object) -> bool:
    if not isinstance(path, (str, os.PathLike)):
        return False

    path_text = os.fspath(path)
    if not path_text:
        return False

    try:
        resolved_path = Path(path_text).resolve(strict=False)
    except OSError:
        return False

    return any(_is_relative_to(resolved_path, root) for root in _DENIED_CODE_ROOTS)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True


def _is_landlock_bootstrap_import(module_name: str) -> bool:
    if module_name not in {"_ctypes", "ctypes"}:
        return False

    if _enabled(_LANDLOCK_BOOTSTRAP_CTYPES_ENVIRONMENT_VARIABLE):
        return True

    for frame in inspect.stack(context=0):
        if not frame.filename.endswith("/docker_sandbox/landlock_runner.py"):
            continue

        return frame.function == "<module>"

    return False


_deny_writable_script_execution()
_deny_writable_spec_from_file_location()
_apply_socket_guards()
_apply_hardware_device_guards()
_apply_process_spawn_guards()
sys.meta_path.insert(0, _DeniedWritableCodeFinder())
sys.meta_path.insert(0, _DeniedModuleFinder())
