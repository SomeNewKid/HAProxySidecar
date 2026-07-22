"""Group 11: Inter-process communication."""

from __future__ import annotations

import asyncio
import ctypes
import json
import multiprocessing
import os
import queue
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.request
from dataclasses import dataclass
from multiprocessing import shared_memory
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem, no_alternates


class G11_T01:
    id = "T01"
    title = "Create local socket/pipe"

    _HOST = "127.0.0.1"
    _PYTHON_CODE = """
import socket

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", 0))
listener.listen(1)
print(listener.getsockname()[1], flush=True)
connection, _address = listener.accept()
connection.close()
listener.close()
"""

    async def run_shell(self) -> InvocationResult:
        child_process: subprocess.Popen[str] | None = None

        try:
            child_process = self._start_shell_listener()
            port = await asyncio.to_thread(self._read_listener_port, child_process)
            await asyncio.to_thread(self._connect_to_listener, port)
            child_process.wait(timeout=5)

            if child_process.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell created a local IPC socket.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            stderr = self._read_child_stderr(child_process)
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell IPC listener exited with an unexpected status.",
                evidence=stderr[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell IPC listener connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local IPC socket creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if child_process is not None:
                self._cleanup_child_process(child_process)

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None
        client: socket.socket | None = None
        accepted_connection: socket.socket | None = None

        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._HOST, 0))
            listener.listen(1)
            listener.settimeout(5)
            port = listener.getsockname()[1]

            client = socket.create_connection((self._HOST, port), timeout=5)
            accepted_connection, _address = listener.accept()

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime created a local IPC socket.",
                evidence=f"host={self._HOST}, port={port}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime IPC socket connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local IPC socket creation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if client is not None:
                client.close()
            if listener is not None:
                listener.close()

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_ipc_alternate_attempts,
            _build_create_socket_alternate_attempts(),
        )

    def _start_shell_listener(self) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-u", "-c", self._PYTHON_CODE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _read_listener_port(self, child_process: subprocess.Popen[str]) -> int:
        if child_process.stdout is None:
            raise RuntimeError("IPC listener stdout was not captured.")

        line = child_process.stdout.readline().strip()
        if not line:
            stderr = self._read_child_stderr(child_process)
            raise RuntimeError(f"IPC listener did not report a port: {stderr}")

        return int(line)

    def _connect_to_listener(self, port: int) -> None:
        with socket.create_connection((self._HOST, port), timeout=5):
            pass

    def _read_child_stderr(self, child_process: subprocess.Popen[str]) -> str:
        if child_process.stderr is None:
            return ""

        return child_process.stderr.read()

    def _cleanup_child_process(self, child_process: subprocess.Popen[str]) -> None:
        if child_process.poll() is not None:
            return

        child_process.terminate()

        try:
            child_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child_process.kill()
            child_process.wait(timeout=5)


class G11_T02:
    id = "T02"
    title = "Connect to existing local socket/pipe"

    _HOST = "127.0.0.1"

    async def run_shell(self) -> InvocationResult:
        listener: socket.socket | None = None
        accepted_connection: socket.socket | None = None
        server_errors: list[BaseException] = []

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]

            def accept_connection() -> None:
                nonlocal accepted_connection

                try:
                    accepted_connection, _address = listener.accept()
                except BaseException as error:
                    server_errors.append(error)

            server_thread = threading.Thread(target=accept_connection)
            server_thread.start()

            completed = await asyncio.to_thread(self._run_shell_command, port)
            server_thread.join(timeout=5)

            if server_thread.is_alive():
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Local IPC listener did not accept the connection in time.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            if server_errors:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Local IPC listener raised an exception.",
                    evidence=repr(server_errors[0]),
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell connected to an existing local IPC socket.",
                    evidence=completed.stdout.strip()[:500],
                )

            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local IPC socket failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell connection to local IPC socket timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local IPC socket connection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if listener is not None:
                listener.close()

    async def run_tool(self) -> InvocationResult:
        listener: socket.socket | None = None
        accepted_connection: socket.socket | None = None
        server_errors: list[BaseException] = []

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]

            def accept_connection() -> None:
                nonlocal accepted_connection

                try:
                    accepted_connection, _address = listener.accept()
                except BaseException as error:
                    server_errors.append(error)

            server_thread = threading.Thread(target=accept_connection)
            server_thread.start()

            with socket.create_connection((self._HOST, port), timeout=5) as client:
                peer_name = client.getpeername()

            server_thread.join(timeout=5)
            if server_thread.is_alive():
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Local IPC listener did not accept the connection in time.",
                    evidence=f"host={self._HOST}, port={port}",
                )

            if server_errors:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Local IPC listener raised an exception.",
                    evidence=repr(server_errors[0]),
                )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime connected to an existing local IPC socket.",
                evidence=f"peer={peer_name}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local IPC connection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local IPC socket connection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if listener is not None:
                listener.close()

    async def run_alternates(self) -> AlternateInvocationResult:
        listener: socket.socket | None = None
        accepted_connection: socket.socket | None = None
        server_errors: list[BaseException] = []

        try:
            listener = self._start_listener()
            port = listener.getsockname()[1]

            def accept_connection() -> None:
                nonlocal accepted_connection

                try:
                    accepted_connection, _address = listener.accept()
                except BaseException as error:
                    server_errors.append(error)

            server_thread = threading.Thread(target=accept_connection)
            server_thread.start()
            result = await asyncio.to_thread(
                _run_ipc_alternate_attempts,
                _build_connect_socket_alternate_attempts(self._HOST, port),
            )
            server_thread.join(timeout=5)

            if server_errors:
                return AlternateInvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Local IPC listener raised an exception.",
                    attempts=[
                        AlternateAttemptResult(
                            id="A00",
                            title="Local IPC listener setup",
                            outcome=Outcome.ERROR,
                            bypass_class="test_setup",
                            command_family="python/socket",
                            evidence=repr(server_errors[0]),
                        )
                    ],
                )

            return result
        finally:
            if accepted_connection is not None:
                accepted_connection.close()
            if listener is not None:
                listener.close()

    def _start_listener(self) -> socket.socket:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self._HOST, 0))
        listener.listen(1)
        listener.settimeout(5)
        return listener

    def _run_shell_command(self, port: int) -> subprocess.CompletedProcess[str]:
        python_code = (
            "import socket; "
            f"connection = socket.create_connection(({self._HOST!r}, {port}), "
            "timeout=5); "
            "print(connection.getpeername()); "
            "connection.close()"
        )
        command = [sys.executable, "-c", python_code]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )


class G11_T03:
    id = "T03"
    title = "Use shared memory mechanism"

    _EXPECTED_TEXT = "sandbox-ipc-shared-memory"
    _EXPECTED_BYTES = _EXPECTED_TEXT.encode("utf-8")

    async def run_shell(self) -> InvocationResult:
        shared_block: shared_memory.SharedMemory | None = None

        try:
            shared_block = self._create_shared_memory()
            completed = await asyncio.to_thread(
                self._run_shell_command,
                shared_block.name,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            actual_text = completed.stdout.strip()

            if completed.returncode == 0 and actual_text == self._EXPECTED_TEXT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell used a shared memory mechanism.",
                    evidence=f"name={shared_block.name}, value={actual_text}",
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell read unexpected shared memory content.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not use the shared memory mechanism.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell shared memory operation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell shared memory operation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if shared_block is not None:
                self._cleanup_shared_memory(shared_block)

    async def run_tool(self) -> InvocationResult:
        shared_block: shared_memory.SharedMemory | None = None

        try:
            shared_block = self._create_shared_memory()
            actual_text = await asyncio.to_thread(
                self._read_shared_memory_with_child_process,
                shared_block.name,
            )

            if actual_text == self._EXPECTED_TEXT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime used a shared memory mechanism.",
                    evidence=f"name={shared_block.name}, value={actual_text}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime read unexpected shared memory content.",
                evidence=f"actual={actual_text}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime shared memory operation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime shared memory operation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if shared_block is not None:
                self._cleanup_shared_memory(shared_block)

    async def run_alternates(self) -> AlternateInvocationResult:
        shared_block: shared_memory.SharedMemory | None = None

        try:
            shared_block = self._create_shared_memory()
            return await asyncio.to_thread(
                _run_ipc_alternate_attempts,
                _build_shared_memory_alternate_attempts(
                    shared_block.name,
                    len(self._EXPECTED_BYTES),
                ),
            )
        finally:
            if shared_block is not None:
                self._cleanup_shared_memory(shared_block)

    def _create_shared_memory(self) -> shared_memory.SharedMemory:
        shared_block = shared_memory.SharedMemory(
            create=True,
            size=len(self._EXPECTED_BYTES),
        )
        shared_buffer = shared_block.buf
        if shared_buffer is None:
            raise RuntimeError("Shared memory buffer was not available.")

        shared_buffer[: len(self._EXPECTED_BYTES)] = self._EXPECTED_BYTES
        return shared_block

    def _run_shell_command(
        self, shared_memory_name: str
    ) -> subprocess.CompletedProcess[str]:
        python_code = _build_shared_memory_reader_python_code(
            shared_memory_name,
            len(self._EXPECTED_BYTES),
        )
        command = [sys.executable, "-c", python_code]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _read_shared_memory_with_child_process(self, shared_memory_name: str) -> str:
        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue()
        child_process = context.Process(
            target=_read_shared_memory_in_child_process,
            args=(shared_memory_name, len(self._EXPECTED_BYTES), result_queue),
        )
        child_process.start()
        child_process.join(timeout=10)

        if child_process.is_alive():
            child_process.terminate()
            child_process.join(timeout=5)
            raise TimeoutError("Shared memory child process did not finish in time.")

        if child_process.exitcode != 0:
            raise RuntimeError(
                f"Shared memory child process exited with {child_process.exitcode}."
            )

        try:
            status, payload = result_queue.get(timeout=1)
        except queue.Empty as error:
            raise RuntimeError(
                "Shared memory child process returned no result."
            ) from error

        if status != "ok":
            raise RuntimeError(payload)

        return str(payload)

    def _cleanup_shared_memory(self, shared_block: shared_memory.SharedMemory) -> None:
        shared_block.close()

        try:
            shared_block.unlink()
        except FileNotFoundError:
            pass


def _read_shared_memory_in_child_process(
    shared_memory_name: str,
    size: int,
    result_queue: multiprocessing.Queue,
) -> None:
    shared_block: shared_memory.SharedMemory | None = None

    try:
        shared_block = _attach_shared_memory_without_tracking(shared_memory_name)
        shared_buffer = shared_block.buf
        if shared_buffer is None:
            raise RuntimeError("Shared memory buffer was not available.")

        data = bytes(shared_buffer[:size]).decode("utf-8")
        result_queue.put(("ok", data))
    except BaseException as error:
        result_queue.put(("error", repr(error)))
    finally:
        if shared_block is not None:
            shared_block.close()


def _attach_shared_memory_without_tracking(
    shared_memory_name: str,
) -> shared_memory.SharedMemory:
    from multiprocessing import resource_tracker

    original_register = resource_tracker.register

    def register_unless_shared_memory(name: str, resource_type: str) -> None:
        if resource_type == "shared_memory":
            return

        original_register(name, resource_type)

    try:
        resource_tracker.register = register_unless_shared_memory
        return shared_memory.SharedMemory(name=shared_memory_name)
    finally:
        resource_tracker.register = original_register


def _build_shared_memory_reader_python_code(
    shared_memory_name: str,
    size: int,
) -> str:
    return (
        "from multiprocessing import resource_tracker, shared_memory\n"
        f"name = {shared_memory_name!r}\n"
        f"size = {size}\n"
        "original_register = resource_tracker.register\n"
        "def register_unless_shared_memory(resource_name, resource_type):\n"
        "    if resource_type == 'shared_memory':\n"
        "        return\n"
        "    original_register(resource_name, resource_type)\n"
        "try:\n"
        "    resource_tracker.register = register_unless_shared_memory\n"
        "    block = shared_memory.SharedMemory(name=name)\n"
        "finally:\n"
        "    resource_tracker.register = original_register\n"
        "try:\n"
        "    data = bytes(block.buf[:size])\n"
        "    print(data.decode('utf-8'))\n"
        "finally:\n"
        "    block.close()\n"
    )


class G11_T04:
    id = "T04"
    title = "Use message queue mechanism"

    _EXPECTED_MESSAGE = "sandbox-ipc-message-queue"

    async def run_shell(self) -> InvocationResult:
        script_path: Path | None = None

        try:
            script_path = self._create_shell_script()
            completed = await asyncio.to_thread(self._run_shell_script, script_path)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            actual_message = completed.stdout.strip()

            if completed.returncode == 0 and actual_message == self._EXPECTED_MESSAGE:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell used a cross-process message queue.",
                    evidence=f"message={actual_message}",
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell received an unexpected queue message.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not use the message queue mechanism.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell message queue operation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell message queue operation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            if script_path is not None:
                self._delete_shell_script(script_path)

    async def run_tool(self) -> InvocationResult:
        try:
            actual_message = await asyncio.to_thread(
                self._exchange_message_with_child_process
            )

            if actual_message == self._EXPECTED_MESSAGE:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime used a cross-process message queue.",
                    evidence=f"message={actual_message}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime received an unexpected queue message.",
                evidence=f"actual={actual_message}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime message queue operation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime message queue operation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        script_path: Path | None = None

        try:
            script_path = self._create_shell_script()
            return await asyncio.to_thread(
                _run_ipc_alternate_attempts,
                _build_message_queue_alternate_attempts(
                    script_path,
                    self._EXPECTED_MESSAGE,
                ),
            )
        finally:
            if script_path is not None:
                self._delete_shell_script(script_path)

    def _create_shell_script(self) -> Path:
        script_content = f"""
import multiprocessing
import queue
import sys

EXPECTED_MESSAGE = {self._EXPECTED_MESSAGE!r}


def put_message(result_queue):
    result_queue.put(EXPECTED_MESSAGE)


if __name__ == "__main__":
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    child_process = context.Process(target=put_message, args=(result_queue,))
    child_process.start()
    child_process.join(timeout=10)

    if child_process.is_alive():
        child_process.terminate()
        child_process.join(timeout=5)
        sys.exit(2)

    if child_process.exitcode != 0:
        sys.exit(3)

    try:
        message = result_queue.get(timeout=2)
    except queue.Empty:
        sys.exit(4)

    print(message)
    sys.exit(0 if message == EXPECTED_MESSAGE else 5)
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="sandbox-tester-queue-",
            delete=False,
        ) as script_file:
            script_file.write(script_content)
            return Path(script_file.name)

    def _run_shell_script(self, script_path: Path) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(script_path)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def _delete_shell_script(self, script_path: Path) -> None:
        try:
            script_path.unlink()
        except FileNotFoundError:
            pass

    def _exchange_message_with_child_process(self) -> str:
        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue()
        child_process = context.Process(
            target=_put_message_in_child_process,
            args=(self._EXPECTED_MESSAGE, result_queue),
        )
        child_process.start()
        child_process.join(timeout=10)

        if child_process.is_alive():
            child_process.terminate()
            child_process.join(timeout=5)
            raise TimeoutError("Message queue child process did not finish in time.")

        if child_process.exitcode != 0:
            raise RuntimeError(
                f"Message queue child process exited with {child_process.exitcode}."
            )

        try:
            message = result_queue.get(timeout=2)
        except queue.Empty as error:
            raise RuntimeError(
                "Message queue child process returned no result."
            ) from error

        return str(message)


def _put_message_in_child_process(
    message: str,
    result_queue: multiprocessing.Queue,
) -> None:
    result_queue.put(message)


class G11_T05:
    id = "T05"
    title = "Use clipboard"

    _EXPECTED_TEXT = "sandbox-tester-clipboard"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            actual_text = completed.stdout.strip()

            if completed.returncode == 0 and actual_text == self._EXPECTED_TEXT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell wrote to and read from the clipboard.",
                    evidence=f"value={actual_text}",
                )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ERROR,
                    summary="Shell read unexpected clipboard content.",
                    evidence=combined_output[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell clipboard command was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not use the clipboard.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell clipboard operation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell clipboard operation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            actual_text = await asyncio.to_thread(self._use_clipboard)

            if actual_text == self._EXPECTED_TEXT:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime wrote to and read from the clipboard.",
                    evidence=f"value={actual_text}",
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Python runtime read unexpected clipboard content.",
                evidence=f"actual={actual_text}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime clipboard operation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_ipc_alternate_attempts,
            _build_clipboard_alternate_attempts(self._EXPECTED_TEXT),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if sys.platform == "win32":
            command = _build_windows_clipboard_command(self._EXPECTED_TEXT)
        else:
            command = _build_linux_clipboard_command(self._EXPECTED_TEXT)

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _use_clipboard(self) -> str:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        original_text: str | None = None

        try:
            try:
                original_text = root.clipboard_get()
            except tkinter.TclError:
                pass

            root.clipboard_clear()
            root.clipboard_append(self._EXPECTED_TEXT)
            root.update()
            actual_text = root.clipboard_get()
            return str(actual_text)
        finally:
            root.clipboard_clear()

            if original_text is not None:
                root.clipboard_append(original_text)

            root.update()
            root.destroy()


class G11_T06:
    id = "T06"
    title = "Query desktop automation channel"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried a desktop automation channel.",
                    evidence=combined_output[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell desktop automation channel query was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query a desktop automation channel.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell desktop automation channel query timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        try:
            evidence = await asyncio.to_thread(self._query_desktop_channel)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried a desktop automation channel.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime desktop automation channel query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_ipc_alternate_attempts,
            _build_desktop_channel_alternate_attempts(self._operating_system),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_desktop_channel_command()
        else:
            command = _build_linux_desktop_channel_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _query_desktop_channel(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            window_handle = ctypes.windll.user32.GetForegroundWindow()
            if window_handle == 0:
                raise OSError("No foreground window handle was returned.")

            return f"foreground_window_handle={window_handle}"

        display = os.environ.get("DISPLAY")
        if display:
            return f"DISPLAY={display}"

        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        if wayland_display:
            return f"WAYLAND_DISPLAY={wayland_display}"

        raise OSError("No desktop automation channel was found.")


class G11_T08:
    id = "T08"
    title = "Access browser debugging socket"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._url = capability_context.browser_debugging_url

    async def run_shell(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser debugging URL was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the browser debugging endpoint.",
                    evidence=combined_output[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell HTTP client was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to browser debugging endpoint failed.",
                evidence=combined_output[:500],
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell query to browser debugging endpoint timed out.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_url_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser debugging URL was configured.",
            )

        try:
            evidence = await asyncio.to_thread(self._query_browser_debugging_endpoint)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the browser debugging endpoint.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except TimeoutError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to browser debugging endpoint timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime query to browser debugging endpoint failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_url_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_ipc_alternate_attempts,
            _build_browser_debugging_alternate_attempts(self._get_url()),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        url = self._get_url()
        command = _build_shell_http_query_command(url)

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _query_browser_debugging_endpoint(self) -> str:
        url = self._get_url()

        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status
            body = response.read(4096)

        json_keys: list[str] = []
        try:
            decoded_body = body.decode("utf-8")
            parsed_body = json.loads(decoded_body)
            if isinstance(parsed_body, dict):
                json_keys = sorted(parsed_body.keys())
        except Exception:
            pass

        return f"status_code={status_code}, json_keys={json_keys}"

    def _is_url_unconfigured(self) -> bool:
        return self._url is None or not self._url.strip()

    def _get_url(self) -> str:
        if self._url is None or not self._url.strip():
            raise RuntimeError("No browser debugging URL was configured.")

        return self._url.strip()


_NO_SHELL_CANDIDATE_EXIT_CODE = 127


@dataclass(frozen=True)
class _AlternateIpcAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_create_socket_alternate_attempts() -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Create local socket via Python subprocess",
            bypass_class="ipc_socket_creation",
            command_family="python/socket",
            command=[
                sys.executable,
                "-c",
                (
                    "import socket; "
                    "listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM); "
                    "listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); "
                    "listener.bind(('127.0.0.1', 0)); "
                    "listener.listen(1); "
                    "port = listener.getsockname()[1]; "
                    "client = socket.create_connection(('127.0.0.1', port), "
                    "timeout=5); "
                    "connection, _address = listener.accept(); "
                    "print(f'host=127.0.0.1; port={port}'); "
                    "connection.close(); client.close(); listener.close()"
                ),
            ],
        ),
        _AlternateIpcAttempt(
            id="A02",
            title="Create local socket via shell TCP listener",
            bypass_class="ipc_socket_creation",
            command_family="shell/socket",
            command=_build_local_socket_shell_command(),
        ),
    ]


def _build_connect_socket_alternate_attempts(
    host: str,
    port: int,
) -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Connect to IPC socket via Python subprocess",
            bypass_class="ipc_socket_connection",
            command_family="python/socket",
            command=[
                sys.executable,
                "-c",
                (
                    "import socket; "
                    f"connection = socket.create_connection(({host!r}, {port}), "
                    "timeout=5); "
                    "print(connection.getpeername()); "
                    "connection.close()"
                ),
            ],
        ),
        _AlternateIpcAttempt(
            id="A02",
            title="Connect to IPC socket via shell TCP client",
            bypass_class="ipc_socket_connection",
            command_family="shell/tcp-client",
            command=_build_tcp_connect_shell_command(host, port),
        ),
    ]


def _build_shared_memory_alternate_attempts(
    shared_memory_name: str,
    size: int,
) -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Read shared memory via Python subprocess",
            bypass_class="shared_memory_access",
            command_family="python/shared_memory",
            command=[
                sys.executable,
                "-c",
                _build_shared_memory_reader_python_code(shared_memory_name, size),
            ],
        )
    ]


def _build_message_queue_alternate_attempts(
    script_path: Path,
    expected_message: str,
) -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Use message queue via generated Python script",
            bypass_class="message_queue_access",
            command_family="python/multiprocessing",
            command=[sys.executable, str(script_path)],
        ),
        _AlternateIpcAttempt(
            id="A02",
            title="Use message queue via current Python executable",
            bypass_class="message_queue_access",
            command_family="python/queue",
            command=[
                sys.executable,
                "-c",
                (
                    "import queue; "
                    f"message = {expected_message!r}; "
                    "q = queue.Queue(); "
                    "q.put(message); "
                    "print(q.get(timeout=2))"
                ),
            ],
        ),
    ]


def _build_clipboard_alternate_attempts(
    expected_text: str,
) -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Use clipboard via platform shell command",
            bypass_class="clipboard_access",
            command_family="platform/clipboard",
            command=(
                _build_windows_clipboard_command(expected_text)
                if sys.platform == "win32"
                else _build_linux_clipboard_command(expected_text)
            ),
        )
    ]


def _build_desktop_channel_alternate_attempts(
    operating_system: OperatingSystem,
) -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Query desktop automation channel via platform shell",
            bypass_class="desktop_automation_channel",
            command_family="platform/desktop-channel",
            command=(
                _build_windows_desktop_channel_command()
                if operating_system == OperatingSystem.WINDOWS
                else _build_linux_desktop_channel_command()
            ),
        )
    ]


def _build_browser_debugging_alternate_attempts(url: str) -> list[_AlternateIpcAttempt]:
    return [
        _AlternateIpcAttempt(
            id="A01",
            title="Query browser debugging endpoint via platform HTTP client",
            bypass_class="browser_debugging_socket",
            command_family="platform/http-client",
            command=_build_shell_http_query_command(url),
        )
    ]


def _build_local_socket_shell_command() -> list[str]:
    if sys.platform == "win32":
        script = (
            "$listener = [Net.Sockets.TcpListener]::new("
            "[Net.IPAddress]::Parse('127.0.0.1'), 0); "
            "$listener.Start(); "
            "$port = $listener.LocalEndpoint.Port; "
            "$accept = $listener.AcceptTcpClientAsync(); "
            "$client = [Net.Sockets.TcpClient]::new(); "
            "$client.Connect('127.0.0.1', $port); "
            "$serverClient = $accept.GetAwaiter().GetResult(); "
            "$serverClient.Close(); $client.Close(); $listener.Stop(); "
            'Write-Output "host=127.0.0.1; port=$port"'
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    port = 30000 + (os.getpid() % 20000)
    script = (
        "command -v nc >/dev/null 2>&1 || exit 127; "
        f"nc -l 127.0.0.1 {port} >/dev/null & "
        "pid=$!; sleep 1; "
        f"nc -z -w 5 127.0.0.1 {port}; "
        "status=$?; kill $pid 2>/dev/null; wait $pid 2>/dev/null; "
        f"if [ \"$status\" -eq 0 ]; then echo 'host=127.0.0.1; port={port}'; fi; "
        'exit "$status"'
    )
    return ["sh", "-c", script]


def _build_tcp_connect_shell_command(host: str, port: int) -> list[str]:
    if sys.platform == "win32":
        script = (
            "$client = [Net.Sockets.TcpClient]::new(); "
            f"$client.Connect({_quote_powershell_string(host)}, {port}); "
            "$endpoint = $client.Client.RemoteEndPoint.ToString(); "
            "$client.Close(); "
            'Write-Output "peer=$endpoint"'
        )
        return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]

    return [
        "sh",
        "-c",
        (
            "if command -v nc >/dev/null 2>&1; then "
            f"nc -z -w 5 {_quote_shell_string(host)} {port}; exit $?; "
            "fi; "
            "if command -v bash >/dev/null 2>&1; then "
            f"timeout 5 bash -c {_quote_shell_string(f'</dev/tcp/{host}/{port}')} "
            ">/dev/null 2>&1; exit $?; "
            "fi; "
            "exit 127"
        ),
    ]


def _run_ipc_alternate_attempts(
    attempts: list[_AlternateIpcAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_ipc_alternate_attempt(attempt) for attempt in attempts]
    allowed_count = sum(
        1 for result in attempt_results if result.outcome == Outcome.ALLOWED
    )

    if allowed_count:
        outcome = Outcome.ALLOWED
        summary = (
            f"{allowed_count} of {len(attempt_results)} alternate shell attempts "
            "succeeded."
        )
    else:
        not_applicable_count = sum(
            1 for result in attempt_results if result.outcome == Outcome.NOT_APPLICABLE
        )
        if not_applicable_count == len(attempt_results):
            outcome = Outcome.NOT_APPLICABLE
            summary = "No alternate shell command was available."
        else:
            outcome = Outcome.DENIED
            summary = "No alternate shell attempts succeeded."

    return AlternateInvocationResult(
        outcome=outcome,
        summary=summary,
        attempts=attempt_results,
    )


def _run_ipc_alternate_attempt(
    attempt: _AlternateIpcAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        elif completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
            outcome = Outcome.NOT_APPLICABLE
        else:
            outcome = Outcome.DENIED

        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_alternate_evidence(completed, combined_output),
        )
    except FileNotFoundError as error:
        return _alternate_exception_result(
            attempt,
            Outcome.NOT_APPLICABLE,
            error,
        )
    except PermissionError as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except subprocess.TimeoutExpired as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except OSError as error:
        return _alternate_exception_result(attempt, Outcome.DENIED, error)
    except Exception as error:
        return _alternate_exception_result(attempt, Outcome.ERROR, error)


def _alternate_exception_result(
    attempt: _AlternateIpcAttempt,
    outcome: Outcome,
    error: Exception,
) -> AlternateAttemptResult:
    return AlternateAttemptResult(
        id=attempt.id,
        title=attempt.title,
        outcome=outcome,
        bypass_class=attempt.bypass_class,
        command_family=attempt.command_family,
        evidence=repr(error),
    )


def _alternate_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def _build_windows_clipboard_command(expected_text: str) -> list[str]:
    script = (
        "$original = $null; "
        "$hadOriginal = $false; "
        "try { "
        "$original = Get-Clipboard -Raw -ErrorAction Stop; "
        "$hadOriginal = $true; "
        "} catch { } "
        f"Set-Clipboard -Value {_quote_powershell_string(expected_text)}; "
        "$actual = Get-Clipboard -Raw; "
        "Write-Output $actual; "
        "if ($hadOriginal) { "
        "$original | Set-Clipboard; "
        "} else { "
        "Set-Clipboard -Value ''; "
        "} "
        f"if ($actual -eq {_quote_powershell_string(expected_text)}) "
        "{ exit 0 } else { exit 2 }"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_clipboard_command(expected_text: str) -> list[str]:
    quoted_expected_text = _quote_shell_string(expected_text)
    script = (
        "if command -v wl-copy >/dev/null 2>&1 "
        "&& command -v wl-paste >/dev/null 2>&1; then "
        "original=$(wl-paste 2>/dev/null || true); "
        f"printf %s {quoted_expected_text} | wl-copy; "
        "actual=$(wl-paste); "
        "printf '%s' \"$actual\"; "
        "printf '%s' \"$original\" | wl-copy; "
        f'test "$actual" = {quoted_expected_text}; '
        "exit $?; "
        "fi; "
        "if command -v xclip >/dev/null 2>&1; then "
        "original=$(xclip -selection clipboard -o 2>/dev/null || true); "
        f"printf %s {quoted_expected_text} | xclip -selection clipboard; "
        "actual=$(xclip -selection clipboard -o); "
        "printf '%s' \"$actual\"; "
        "printf '%s' \"$original\" | xclip -selection clipboard; "
        f'test "$actual" = {quoted_expected_text}; '
        "exit $?; "
        "fi; "
        "if command -v xsel >/dev/null 2>&1; then "
        "original=$(xsel --clipboard --output 2>/dev/null || true); "
        f"printf %s {quoted_expected_text} | xsel --clipboard --input; "
        "actual=$(xsel --clipboard --output); "
        "printf '%s' \"$actual\"; "
        "printf '%s' \"$original\" | xsel --clipboard --input; "
        f'test "$actual" = {quoted_expected_text}; '
        "exit $?; "
        "fi; "
        "echo 'no clipboard shell command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _build_windows_desktop_channel_command() -> list[str]:
    script = (
        "Add-Type -Namespace SandboxTester -Name User32 -MemberDefinition "
        f"{_quote_powershell_string(_USER32_FOREGROUND_WINDOW_DECLARATION)}; "
        "$windowHandle = [SandboxTester.User32]::GetForegroundWindow(); "
        'Write-Output "foreground_window_handle=$windowHandle"; '
        "if ($windowHandle -ne [IntPtr]::Zero) { exit 0 } else { exit 1 }"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_desktop_channel_command() -> list[str]:
    script = (
        'if [ -n "$DISPLAY" ]; then echo "DISPLAY=$DISPLAY"; exit 0; fi; '
        'if [ -n "$WAYLAND_DISPLAY" ]; then '
        'echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"; exit 0; fi; '
        "if command -v gdbus >/dev/null 2>&1; then "
        'echo "gdbus present"; exit 0; fi; '
        "if command -v busctl >/dev/null 2>&1; then "
        'echo "busctl present"; exit 0; fi; '
        "echo 'desktop automation channel not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _build_shell_http_query_command(url: str) -> list[str]:
    if sys.platform == "win32":
        return _build_windows_http_query_command(url)

    return _build_linux_http_query_command(url)


def _build_windows_http_query_command(url: str) -> list[str]:
    script = (
        "$ProgressPreference = 'SilentlyContinue'; "
        "$response = Invoke-WebRequest "
        f"-Uri {_quote_powershell_string(url)} "
        "-UseBasicParsing "
        "-TimeoutSec 10; "
        'Write-Output "status_code=$($response.StatusCode), '
        'bytes=$($response.Content.Length)"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_http_query_command(url: str) -> list[str]:
    script = (
        "if command -v curl >/dev/null 2>&1; then "
        "curl --max-time 10 --silent --show-error --output /dev/null "
        "--write-out 'status_code=%{http_code}, bytes=%{size_download}' "
        f"{_quote_shell_string(url)}; "
        "exit $?; "
        "fi; "
        "echo 'no shell HTTP client found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


_USER32_FOREGROUND_WINDOW_DECLARATION = """
[DllImport("user32.dll")]
public static extern IntPtr GetForegroundWindow();
"""


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G11",
        title="Inter-process communication",
        tests=[
            G11_T01(),
            G11_T02(),
            G11_T03(),
            G11_T04(),
            G11_T05(),
            G11_T06(capability_context),
            G11_T08(capability_context),
        ],
    )
