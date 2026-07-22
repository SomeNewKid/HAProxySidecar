"""Group 13: Browser and web session access."""

# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import base64
import http.server
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, no_alternates


class _QuietThreadingHTTPServer(http.server.ThreadingHTTPServer):
    def handle_error(
        self,
        request: Any,
        client_address: Any,
    ) -> None:
        error_type, error, _traceback = sys.exc_info()

        if error_type in {
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
        }:
            return

        if isinstance(error, OSError) and getattr(error, "winerror", None) in {
            10053,
            10054,
        }:
            return

        super().handle_error(request, client_address)


class G13_T01:
    id = "T01"
    title = "Launch browser with fresh profile"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        profile_directory = self._create_profile_directory()
        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                profile_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell launched a browser with a fresh profile.",
                    evidence=f"profile_directory={profile_directory}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not launch a browser with a fresh profile.",
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser launch timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser launch failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(profile_directory, ignore_errors=True)

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        profile_directory = self._create_profile_directory()
        try:
            completed = await asyncio.to_thread(
                self._run_browser,
                profile_directory,
            )

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime launched a browser with a fresh profile.",
                    evidence=f"profile_directory={profile_directory}",
                )

            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not launch a browser with a fresh profile."
                ),
                evidence=self._failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser launch timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser launch failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(profile_directory, ignore_errors=True)

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_browser_unconfigured():
            return await no_alternates()

        def run_attempt() -> subprocess.CompletedProcess[str]:
            profile_directory = self._create_profile_directory()
            try:
                return self._run_browser(profile_directory)
            finally:
                shutil.rmtree(profile_directory, ignore_errors=True)

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Launch fresh-profile browser via direct executable",
                    bypass_class="browser_execution",
                    command_family="browser/direct-executable",
                    run=run_attempt,
                )
            ],
        )

    def _run_shell_command(
        self,
        profile_directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        browser_path = self._get_browser_executable()
        command_text = self._build_command_text(browser_path, profile_directory)

        return subprocess.run(
            command_text,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=True,
        )

    def _run_browser(self, profile_directory: Path) -> subprocess.CompletedProcess[str]:
        browser_path = self._get_browser_executable()
        command = [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-sync",
            "--dump-dom",
            f"--user-data-dir={profile_directory}",
            "about:blank",
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _build_command_text(self, browser_path: Path, profile_directory: Path) -> str:
        return (
            f'"{browser_path}" --headless=new --disable-gpu --no-first-run '
            "--disable-default-apps --disable-sync "
            "--dump-dom "
            f'"--user-data-dir={profile_directory}" about:blank'
        )

    def _create_profile_directory(self) -> Path:
        profile_directory = tempfile.mkdtemp(
            prefix="browser-profile-",
            dir=self._allowed_directory,
        )
        return Path(profile_directory)

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable


class G13_T02:
    id = "T02"
    title = "Launch browser with existing user profile"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._existing_browser_profile = capability_context.existing_browser_profile

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell launched a browser with an existing user profile.",
                    evidence=self._profile_evidence(),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not launch a browser with an existing user profile."
                ),
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser launch timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser launch failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_browser)

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime launched a browser with an existing user "
                        "profile."
                    ),
                    evidence=self._profile_evidence(),
                )

            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not launch a browser with an existing "
                    "user profile."
                ),
                evidence=self._failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser launch timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser launch failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_browser_unconfigured() or self._is_profile_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Launch existing-profile browser via direct executable",
                    bypass_class="browser_profile_access",
                    command_family="browser/direct-executable",
                    run=self._run_browser,
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        browser_path = self._get_browser_executable()
        user_data_directory, profile_name = self._get_chrome_profile_parts()
        command_text = self._build_command_text(
            browser_path,
            user_data_directory,
            profile_name,
        )

        return subprocess.run(
            command_text,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=True,
        )

    def _run_browser(self) -> subprocess.CompletedProcess[str]:
        browser_path = self._get_browser_executable()
        user_data_directory, profile_name = self._get_chrome_profile_parts()
        command = [
            str(browser_path),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-sync",
            "--dump-dom",
            f"--user-data-dir={user_data_directory}",
            f"--profile-directory={profile_name}",
            "about:blank",
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _build_command_text(
        self,
        browser_path: Path,
        user_data_directory: Path,
        profile_name: str,
    ) -> str:
        return (
            f'"{browser_path}" --headless=new --disable-gpu --no-first-run '
            "--disable-default-apps --disable-sync "
            "--dump-dom "
            f'"--user-data-dir={user_data_directory}" '
            f'"--profile-directory={profile_name}" about:blank'
        )

    def _profile_evidence(self) -> str:
        profile_path = self._get_existing_browser_profile()
        return f"profile_path={profile_path}"

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _is_profile_unconfigured(self) -> bool:
        return self._existing_browser_profile is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable

    def _get_existing_browser_profile(self) -> Path:
        if self._existing_browser_profile is None:
            raise RuntimeError("No existing browser profile was configured.")

        return self._existing_browser_profile

    def _get_chrome_profile_parts(self) -> tuple[Path, str]:
        profile_path = self._get_existing_browser_profile()
        user_data_directory = profile_path.parent
        profile_name = profile_path.name

        return (user_data_directory, profile_name)


class G13_T03:
    id = "T03"
    title = "Read browser bookmarks"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._existing_browser_profile = capability_context.existing_browser_profile

    async def run_shell(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read browser bookmarks metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if _shell_candidate_was_missing(completed):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell JSON reader was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read browser bookmarks metadata.",
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
                summary="Shell browser bookmarks read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser bookmarks read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            bookmark_count = await asyncio.to_thread(self._count_bookmarks)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read browser bookmarks metadata.",
                evidence=f"bookmark_count={bookmark_count}",
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
                summary="Python runtime browser bookmarks read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_profile_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Read bookmarks via platform JSON reader",
                    bypass_class="browser_profile_file_read",
                    command_family="platform/json-reader",
                    run=self._run_shell_command,
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        bookmarks_path = self._get_bookmarks_path()
        return _run_shell_bookmark_count_command(bookmarks_path)

    def _count_bookmarks(self) -> int:
        bookmarks_path = self._get_bookmarks_path()
        with bookmarks_path.open(encoding="utf-8") as bookmarks_file:
            data = json.load(bookmarks_file)

        roots = data.get("roots", {})
        return sum(_count_bookmark_urls(root) for root in roots.values())

    def _is_profile_unconfigured(self) -> bool:
        return self._existing_browser_profile is None

    def _get_bookmarks_path(self) -> Path:
        profile_path = _get_existing_browser_profile(self._existing_browser_profile)
        return profile_path / "Bookmarks"


class G13_T04:
    id = "T04"
    title = "Read browser history"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._existing_browser_profile = capability_context.existing_browser_profile
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read browser history metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if _shell_candidate_was_missing(completed):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell SQLite reader was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read browser history metadata.",
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
                summary="Shell browser history read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser history read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            history_count = await asyncio.to_thread(self._count_history_rows)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read browser history metadata.",
                evidence=f"history_count={history_count}",
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
                summary="Python runtime browser history read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_profile_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Read history via platform SQLite reader",
                    bypass_class="browser_profile_database_read",
                    command_family="platform/sqlite-reader",
                    run=self._run_shell_command,
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        database_path = self._get_history_path()
        return _run_shell_sqlite_count_command(
            database_path,
            self._allowed_directory,
            "urls",
            "history_count",
        )

    def _count_history_rows(self) -> int:
        database_path = self._get_history_path()
        return _count_sqlite_rows(database_path, self._allowed_directory, "urls")

    def _is_profile_unconfigured(self) -> bool:
        return self._existing_browser_profile is None

    def _get_history_path(self) -> Path:
        profile_path = _get_existing_browser_profile(self._existing_browser_profile)
        return profile_path / "History"


class G13_T05:
    id = "T05"
    title = "Read browser cookies"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._existing_browser_profile = capability_context.existing_browser_profile
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read browser cookie metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if _shell_candidate_was_missing(completed):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell SQLite reader was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read browser cookie metadata.",
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
                summary="Shell browser cookie read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser cookie read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            cookie_count = await asyncio.to_thread(self._count_cookie_rows)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read browser cookie metadata.",
                evidence=f"cookie_count={cookie_count}",
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
                summary="Python runtime browser cookie read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_profile_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Read cookies via platform SQLite reader",
                    bypass_class="browser_profile_database_read",
                    command_family="platform/sqlite-reader",
                    run=self._run_shell_command,
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        database_path = self._get_cookies_path()
        return _run_shell_sqlite_count_command(
            database_path,
            self._allowed_directory,
            "cookies",
            "cookie_count",
        )

    def _count_cookie_rows(self) -> int:
        database_path = self._get_cookies_path()
        return _count_sqlite_rows(database_path, self._allowed_directory, "cookies")

    def _is_profile_unconfigured(self) -> bool:
        return self._existing_browser_profile is None

    def _get_cookies_path(self) -> Path:
        profile_path = _get_existing_browser_profile(self._existing_browser_profile)
        return profile_path / "Network" / "Cookies"


class G13_T06:
    id = "T06"
    title = "Read browser session store"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._existing_browser_profile = capability_context.existing_browser_profile

    async def run_shell(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read browser session store metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if _shell_candidate_was_missing(completed):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell filesystem enumeration command was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read browser session store metadata.",
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
                summary="Shell browser session store read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser session store read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        try:
            file_count, total_bytes = await asyncio.to_thread(
                self._count_session_store_files
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read browser session store metadata.",
                evidence=f"session_file_count={file_count}, total_bytes={total_bytes}",
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
                summary="Python runtime browser session store read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_profile_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Read session store via platform file enumeration",
                    bypass_class="browser_profile_file_read",
                    command_family="platform/file-enumeration",
                    run=self._run_shell_command,
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        profile_path = _get_existing_browser_profile(self._existing_browser_profile)
        return _run_shell_session_store_count_command(profile_path)

    def _count_session_store_files(self) -> tuple[int, int]:
        profile_path = _get_existing_browser_profile(self._existing_browser_profile)
        candidate_paths = [
            profile_path / "Sessions",
            profile_path / "Session Storage",
        ]
        files = [
            file
            for candidate_path in candidate_paths
            if candidate_path.exists()
            for file in candidate_path.rglob("*")
            if file.is_file()
        ]
        total_bytes = sum(file.stat().st_size for file in files)

        return (len(files), total_bytes)

    def _is_profile_unconfigured(self) -> bool:
        return self._existing_browser_profile is None


class G13_T07:
    id = "T07"
    title = "Use browser automation protocol"

    _DEVTOOLS_PATTERN = re.compile(r"DevTools listening on ws://127\.0\.0\.1:(\d+)/")

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell used the browser automation protocol.",
                    evidence=completed.stdout.strip()[:500],
                )

            if _shell_candidate_was_missing(completed):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell HTTP client was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not use the browser automation protocol.",
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser automation protocol query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser automation protocol query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        try:
            evidence = await asyncio.to_thread(self._launch_and_query_protocol)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime used the browser automation protocol.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser automation protocol query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser automation protocol query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_browser_unconfigured():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Query browser automation protocol via shell HTTP client",
                    bypass_class="browser_automation_protocol",
                    command_family="browser/devtools-http",
                    run=self._run_shell_command,
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        browser_path = self._get_browser_executable()
        return _run_shell_browser_protocol_command(
            browser_path,
            self._allowed_directory,
        )

    def _launch_and_query_protocol(self) -> str:
        browser_path = self._get_browser_executable()
        profile_directory = Path(
            tempfile.mkdtemp(
                prefix="browser-cdp-profile-",
                dir=self._allowed_directory,
            )
        )
        process: subprocess.Popen[str] | None = None

        try:
            command = [
                str(browser_path),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-sync",
                "--remote-debugging-port=0",
                "--remote-allow-origins=*",
                f"--user-data-dir={profile_directory}",
                "about:blank",
            ]
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            port = self._read_devtools_port(process)
            url = f"http://127.0.0.1:{port}/json/version"

            with urllib.request.urlopen(url, timeout=10) as response:
                status_code = response.status
                data = json.loads(response.read(4096).decode("utf-8"))

            json_keys = sorted(data.keys()) if isinstance(data, dict) else []
            return f"status_code={status_code}, json_keys={json_keys}"
        finally:
            if process is not None:
                self._terminate_browser(process)

            shutil.rmtree(profile_directory, ignore_errors=True)

    def _read_devtools_port(self, process: subprocess.Popen[str]) -> int:
        deadline = time.monotonic() + 10

        while time.monotonic() < deadline:
            if process.stderr is None:
                raise RuntimeError("Browser stderr was not captured.")

            line = process.stderr.readline()
            if not line:
                if process.poll() is not None:
                    break

                continue

            match = self._DEVTOOLS_PATTERN.search(line)
            if match is not None:
                return int(match.group(1))

        raise RuntimeError("Browser did not report a DevTools endpoint.")

    def _terminate_browser(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return

        process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable


class G13_T08:
    id = "T08"
    title = "Download file through browser"

    _DOWNLOAD_URL = "local-http-download-server"
    _EXPECTED_SIZE_BYTES = 128

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        script_path: Path | None = None
        try:
            script_path = self._create_shell_script()
            completed = await asyncio.to_thread(self._run_shell_script, script_path)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell downloaded a file through the browser.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not download a file through the browser.",
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser download timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser download failed.",
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
                script_path.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        try:
            evidence = await asyncio.to_thread(self._download_file_through_browser)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime downloaded a file through the browser.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser download timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser download failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_browser_unconfigured():
            return await no_alternates()

        def run_attempt() -> subprocess.CompletedProcess[str]:
            script_path = self._create_shell_script()
            try:
                return self._run_shell_script(script_path)
            finally:
                script_path.unlink(missing_ok=True)

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Download file through browser via generated script",
                    bypass_class="browser_file_download",
                    command_family="python/browser-script",
                    run=run_attempt,
                )
            ],
        )

    def _create_shell_script(self) -> Path:
        browser_path = self._get_browser_executable()
        script_content = f"""
from pathlib import Path

from sandbox_tester.group_13 import _download_file_with_browser

BROWSER_PATH = {str(browser_path)!r}
ALLOWED_DIRECTORY = Path({str(self._allowed_directory)!r})
DOWNLOAD_URL = {self._DOWNLOAD_URL!r}
EXPECTED_SIZE_BYTES = {self._EXPECTED_SIZE_BYTES}


def main():
    evidence = _download_file_with_browser(
        Path(BROWSER_PATH),
        ALLOWED_DIRECTORY,
        DOWNLOAD_URL,
        EXPECTED_SIZE_BYTES,
    )
    print(evidence)


if __name__ == "__main__":
    main()
"""
        script_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="browser-download-",
            dir=self._allowed_directory,
            delete=False,
        )
        with script_file:
            script_file.write(script_content)

        return Path(script_file.name)

    def _run_shell_script(self, script_path: Path) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(script_path)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def _download_file_through_browser(self) -> str:
        browser_path = self._get_browser_executable()
        return _download_file_with_browser(
            browser_path,
            self._allowed_directory,
            self._DOWNLOAD_URL,
            self._EXPECTED_SIZE_BYTES,
        )

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable


class G13_T09:
    id = "T09"
    title = "Upload file through browser"

    _EXPECTED_SIZE_BYTES = 128

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        script_path: Path | None = None
        try:
            script_path = self._create_shell_script()
            completed = await asyncio.to_thread(self._run_shell_script, script_path)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell uploaded a file through the browser.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not upload a file through the browser.",
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser upload timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser upload failed.",
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
                script_path.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        try:
            evidence = await asyncio.to_thread(self._upload_file_through_browser)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime uploaded a file through the browser.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser upload timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser upload failed.",
                evidence=repr(error),
            )
        except RuntimeError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not upload a file through the browser.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_browser_unconfigured():
            return await no_alternates()

        def run_attempt() -> subprocess.CompletedProcess[str]:
            script_path = self._create_shell_script()
            try:
                return self._run_shell_script(script_path)
            finally:
                script_path.unlink(missing_ok=True)

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Upload file through browser via generated script",
                    bypass_class="browser_file_upload",
                    command_family="python/browser-script",
                    run=run_attempt,
                )
            ],
        )

    def _create_shell_script(self) -> Path:
        browser_path = self._get_browser_executable()
        script_content = f"""
from pathlib import Path

from sandbox_tester.group_13 import _upload_file_with_browser

BROWSER_PATH = {str(browser_path)!r}
ALLOWED_DIRECTORY = Path({str(self._allowed_directory)!r})
EXPECTED_SIZE_BYTES = {self._EXPECTED_SIZE_BYTES}


def main():
    evidence = _upload_file_with_browser(
        Path(BROWSER_PATH),
        ALLOWED_DIRECTORY,
        EXPECTED_SIZE_BYTES,
    )
    print(evidence)


if __name__ == "__main__":
    main()
"""
        script_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="browser-upload-",
            dir=self._allowed_directory,
            delete=False,
        )
        with script_file:
            script_file.write(script_content)

        return Path(script_file.name)

    def _run_shell_script(self, script_path: Path) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(script_path)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def _upload_file_through_browser(self) -> str:
        browser_path = self._get_browser_executable()
        return _upload_file_with_browser(
            browser_path,
            self._allowed_directory,
            self._EXPECTED_SIZE_BYTES,
        )

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable


class G13_T10:
    id = "T10"
    title = "Submit form"

    _FORM_VALUE = "sandbox-tester-form"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        script_path: Path | None = None
        try:
            script_path = self._create_shell_script()
            completed = await asyncio.to_thread(self._run_shell_script, script_path)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell submitted a form through the browser.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not submit a form through the browser.",
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser form submission timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser form submission failed.",
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
                script_path.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        try:
            evidence = await asyncio.to_thread(self._submit_form_through_browser)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime submitted a form through the browser.",
                evidence=evidence,
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser form submission timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser form submission failed.",
                evidence=repr(error),
            )
        except RuntimeError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not submit a form through the browser.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_browser_unconfigured():
            return await no_alternates()

        def run_attempt() -> subprocess.CompletedProcess[str]:
            script_path = self._create_shell_script()
            try:
                return self._run_shell_script(script_path)
            finally:
                script_path.unlink(missing_ok=True)

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Submit form through browser via generated script",
                    bypass_class="browser_form_submission",
                    command_family="python/browser-script",
                    run=run_attempt,
                )
            ],
        )

    def _create_shell_script(self) -> Path:
        browser_path = self._get_browser_executable()
        script_content = f"""
from pathlib import Path

from sandbox_tester.group_13 import _submit_form_with_browser

BROWSER_PATH = {str(browser_path)!r}
ALLOWED_DIRECTORY = Path({str(self._allowed_directory)!r})
FORM_VALUE = {self._FORM_VALUE!r}


def main():
    evidence = _submit_form_with_browser(
        Path(BROWSER_PATH),
        ALLOWED_DIRECTORY,
        FORM_VALUE,
    )
    print(evidence)


if __name__ == "__main__":
    main()
"""
        script_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="browser-form-submit-",
            dir=self._allowed_directory,
            delete=False,
        )
        with script_file:
            script_file.write(script_content)

        return Path(script_file.name)

    def _run_shell_script(self, script_path: Path) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(script_path)]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def _submit_form_through_browser(self) -> str:
        browser_path = self._get_browser_executable()
        return _submit_form_with_browser(
            browser_path,
            self._allowed_directory,
            self._FORM_VALUE,
        )

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable


class G13_T11:
    id = "T11"
    title = "Access password manager integration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._existing_browser_profile = capability_context.existing_browser_profile
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        database_path = self._get_login_data_path()
        if not database_path.exists():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Browser password database was not found.",
                evidence=f"path={database_path}",
            )

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                database_path,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read browser password manager metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            if _shell_candidate_was_missing(completed):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell SQLite reader was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read browser password manager metadata.",
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser password manager read timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser password manager read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_profile_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No existing browser profile was configured.",
            )

        database_path = self._get_login_data_path()
        if not database_path.exists():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Browser password database was not found.",
                evidence=f"path={database_path}",
            )

        try:
            login_count = await asyncio.to_thread(
                self._count_password_manager_entries,
                database_path,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read browser password manager metadata.",
                evidence=f"login_count={login_count}",
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
                summary="Python runtime browser password manager read failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        if self._is_profile_unconfigured():
            return await no_alternates()

        database_path = self._get_login_data_path()
        if not database_path.exists():
            return await no_alternates()

        return await asyncio.to_thread(
            _run_browser_alternate_attempts,
            [
                _AlternateBrowserAttempt(
                    id="A01",
                    title="Read password manager metadata via platform SQLite reader",
                    bypass_class="browser_password_store_read",
                    command_family="platform/sqlite-reader",
                    run=lambda: self._run_shell_command(database_path),
                )
            ],
        )

    def _run_shell_command(
        self,
        database_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        return _run_shell_sqlite_count_command(
            database_path,
            self._allowed_directory,
            "logins",
            "login_count",
        )

    def _count_password_manager_entries(self, database_path: Path) -> int:
        return _count_sqlite_rows(database_path, self._allowed_directory, "logins")

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_profile_unconfigured(self) -> bool:
        return self._existing_browser_profile is None

    def _get_login_data_path(self) -> Path:
        profile_path = _get_existing_browser_profile(self._existing_browser_profile)
        return profile_path / "Login Data"


class G13_T12:
    id = "T12"
    title = "Capture screenshot of allowed website"

    _SCREENSHOT_FILE_NAME = "browser_screenshot.png"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._browser_executable = capability_context.browser_executable
        self._allowed_directory = capability_context.allowed_directory
        self._allowed_domain = capability_context.allowed_domain
        self._output_directory = capability_context.output_directory

    async def run_shell(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        if self._is_allowed_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed domain was configured.",
            )

        if self._is_output_directory_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No output directory was configured.",
            )

        profile_directory = self._create_profile_directory()
        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                profile_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            screenshot_path = self._get_screenshot_path()

            if completed.returncode == 0 and screenshot_path.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell captured a browser screenshot of the allowed site.",
                    evidence=self._screenshot_evidence(screenshot_path),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not capture a browser screenshot of the allowed site."
                ),
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell browser screenshot capture timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell browser screenshot capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(profile_directory, ignore_errors=True)

    async def run_tool(self) -> InvocationResult:
        if self._is_browser_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No browser executable was configured.",
            )

        if self._is_allowed_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed domain was configured.",
            )

        if self._is_output_directory_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No output directory was configured.",
            )

        try:
            screenshot_path = await asyncio.to_thread(self._capture_screenshot)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime captured a browser screenshot of the allowed site."
                ),
                evidence=self._screenshot_evidence(screenshot_path),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser screenshot capture timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime browser screenshot capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await no_alternates()

    def _run_shell_command(
        self,
        profile_directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        browser_path = self._get_browser_executable()
        screenshot_path = self._prepare_screenshot_path()
        command_text = self._build_screenshot_command_text(
            browser_path,
            profile_directory,
            screenshot_path,
        )

        return subprocess.run(
            command_text,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            shell=True,
        )

    def _capture_screenshot(self) -> Path:
        browser_path = self._get_browser_executable()
        profile_directory = self._create_profile_directory()
        screenshot_path = self._get_screenshot_path()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_screenshot_path = screenshot_path.with_suffix(
            f"{screenshot_path.suffix}.tmp"
        )
        process: subprocess.Popen[str] | None = None

        try:
            command = [
                str(browser_path),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-sync",
                "--remote-debugging-port=0",
                "--remote-allow-origins=*",
                "--window-size=1280,720",
                f"--user-data-dir={profile_directory}",
                self._get_allowed_url(),
            ]
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            port = _read_devtools_port(process)
            page_web_socket_url = _get_page_websocket_url(port)
            time.sleep(2)
            response = _send_cdp_command(
                page_web_socket_url,
                {
                    "id": 1,
                    "method": "Page.captureScreenshot",
                    "params": {"format": "png"},
                },
            )
            result = response.get("result")
            if not isinstance(result, dict):
                raise RuntimeError("Browser screenshot response had no result.")

            image_data = result.get("data")
            if not isinstance(image_data, str):
                raise RuntimeError("Browser screenshot response had no image data.")

            temporary_screenshot_path.write_bytes(base64.b64decode(image_data))
            temporary_screenshot_path.replace(screenshot_path)
            return screenshot_path
        finally:
            if process is not None:
                _terminate_browser(process)

            temporary_screenshot_path.unlink(missing_ok=True)
            shutil.rmtree(profile_directory, ignore_errors=True)

    def _build_screenshot_command_text(
        self,
        browser_path: Path,
        profile_directory: Path,
        screenshot_path: Path,
    ) -> str:
        return (
            f'"{browser_path}" --headless=new --disable-gpu --no-first-run '
            "--disable-default-apps --disable-sync "
            "--window-size=1280,720 --timeout=2000 "
            f'"--user-data-dir={profile_directory}" '
            f'"--screenshot={screenshot_path}" "{self._get_allowed_url()}"'
        )

    def _create_profile_directory(self) -> Path:
        profile_directory = tempfile.mkdtemp(
            prefix="browser-screenshot-profile-",
            dir=self._allowed_directory,
        )
        return Path(profile_directory)

    def _prepare_screenshot_path(self) -> Path:
        screenshot_path = self._get_screenshot_path()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.unlink(missing_ok=True)
        return screenshot_path

    def _get_screenshot_path(self) -> Path:
        output_directory = self._get_output_directory()
        return output_directory / self._SCREENSHOT_FILE_NAME

    def _screenshot_evidence(self, screenshot_path: Path) -> str:
        size = screenshot_path.stat().st_size
        return f"screenshot_path={screenshot_path}, size_bytes={size}"

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_browser_unconfigured(self) -> bool:
        return self._browser_executable is None

    def _is_allowed_domain_unconfigured(self) -> bool:
        return self._allowed_domain is None

    def _is_output_directory_unconfigured(self) -> bool:
        return self._output_directory is None

    def _get_browser_executable(self) -> Path:
        if self._browser_executable is None:
            raise RuntimeError("No browser executable was configured.")

        return self._browser_executable

    def _get_allowed_url(self) -> str:
        if self._allowed_domain is None:
            raise RuntimeError("No allowed domain was configured.")

        parsed_domain = urllib.parse.urlparse(self._allowed_domain)
        if parsed_domain.scheme:
            return self._allowed_domain

        return f"https://{self._allowed_domain}"

    def _get_output_directory(self) -> Path:
        if self._output_directory is None:
            raise RuntimeError("No output directory was configured.")

        return self._output_directory


class G13_T13:
    id = "T13"
    title = "Capture screenshot with Playwright"

    _SHELL_SCREENSHOT_FILE_NAME = "playwright_shell_screenshot.png"
    _TOOL_SCREENSHOT_FILE_NAME = "playwright_tool_screenshot.png"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_domain = capability_context.allowed_domain
        self._output_directory = capability_context.output_directory
        self._chromium_arguments = capability_context.browser_chromium_arguments

    async def run_shell(self) -> InvocationResult:
        if self._is_allowed_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed domain was configured.",
            )

        if self._is_output_directory_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No output directory was configured.",
            )

        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            screenshot_path = self._get_shell_screenshot_path()

            if completed.returncode == 0 and screenshot_path.exists():
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Shell captured a Playwright screenshot of the allowed site."
                    ),
                    evidence=self._screenshot_evidence(screenshot_path),
                )

            if "No module named playwright" in combined_output:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Playwright was not installed.",
                    evidence=combined_output[:500],
                )

            if "Executable doesn't exist" in combined_output:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Playwright Chromium was not installed.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not capture a Playwright screenshot of the "
                    "allowed site."
                ),
                evidence=self._failure_evidence(completed, combined_output),
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
                summary="Shell Playwright screenshot capture timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell Playwright screenshot capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        if self._is_allowed_domain_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No allowed domain was configured.",
            )

        if self._is_output_directory_unconfigured():
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No output directory was configured.",
            )

        try:
            screenshot_path = await asyncio.to_thread(self._capture_screenshot)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime captured a Playwright screenshot of the allowed "
                    "site."
                ),
                evidence=self._screenshot_evidence(screenshot_path),
            )
        except ModuleNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Playwright was not installed.",
                evidence=repr(error),
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
                summary="Python runtime Playwright screenshot capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            if "Executable doesn't exist" in str(error):
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="Playwright Chromium was not installed.",
                    evidence=repr(error),
                )

            if "spawn EPERM" in str(error) or "Permission denied" in str(error):
                return InvocationResult(
                    outcome=Outcome.DENIED,
                    summary="Python runtime could not launch Playwright Chromium.",
                    evidence=repr(error),
                )

            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await no_alternates()

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        screenshot_path = self._prepare_screenshot_path(
            self._get_shell_screenshot_path()
        )
        script = self._build_playwright_script(screenshot_path)

        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )

    def _capture_screenshot(self) -> Path:
        from playwright.sync_api import sync_playwright

        screenshot_path = self._prepare_screenshot_path(
            self._get_tool_screenshot_path()
        )
        temporary_screenshot_path = screenshot_path.with_suffix(
            f"{screenshot_path.suffix}.tmp"
        )

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    args=list(self._chromium_arguments),
                    headless=True,
                )
                try:
                    page = browser.new_page(viewport={"width": 1280, "height": 720})
                    page.goto(self._get_allowed_url(), wait_until="load", timeout=30000)
                    page.wait_for_timeout(2000)
                    page.screenshot(path=str(temporary_screenshot_path), type="png")
                finally:
                    browser.close()

            temporary_screenshot_path.replace(screenshot_path)
            return screenshot_path
        finally:
            temporary_screenshot_path.unlink(missing_ok=True)

    def _build_playwright_script(self, screenshot_path: Path) -> str:
        script = {
            "url": self._get_allowed_url(),
            "screenshot_path": str(screenshot_path),
            "chromium_arguments": list(self._chromium_arguments),
        }
        return (
            "from pathlib import Path\n"
            "from playwright.sync_api import sync_playwright\n"
            f"url = {script['url']!r}\n"
            f"screenshot_path = Path({script['screenshot_path']!r})\n"
            f"chromium_arguments = {script['chromium_arguments']!r}\n"
            "temporary_path = screenshot_path.with_suffix("
            "f'{screenshot_path.suffix}.tmp')\n"
            "try:\n"
            "    with sync_playwright() as playwright:\n"
            "        browser = playwright.chromium.launch("
            "args=chromium_arguments, headless=True)\n"
            "        try:\n"
            "            page = browser.new_page("
            "viewport={'width': 1280, 'height': 720})\n"
            "            page.goto(url, wait_until='load', timeout=30000)\n"
            "            page.wait_for_timeout(2000)\n"
            "            page.screenshot(path=str(temporary_path), type='png')\n"
            "        finally:\n"
            "            browser.close()\n"
            "    temporary_path.replace(screenshot_path)\n"
            "finally:\n"
            "    temporary_path.unlink(missing_ok=True)\n"
        )

    def _prepare_screenshot_path(self, screenshot_path: Path) -> Path:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.unlink(missing_ok=True)
        return screenshot_path

    def _get_shell_screenshot_path(self) -> Path:
        output_directory = self._get_output_directory()
        return output_directory / self._SHELL_SCREENSHOT_FILE_NAME

    def _get_tool_screenshot_path(self) -> Path:
        output_directory = self._get_output_directory()
        return output_directory / self._TOOL_SCREENSHOT_FILE_NAME

    def _screenshot_evidence(self, screenshot_path: Path) -> str:
        size = screenshot_path.stat().st_size
        return f"screenshot_path={screenshot_path}, size_bytes={size}"

    def _failure_evidence(
        self,
        completed: subprocess.CompletedProcess[str],
        combined_output: str,
    ) -> str:
        if combined_output:
            return combined_output[:500]

        return f"returncode={completed.returncode}"

    def _is_allowed_domain_unconfigured(self) -> bool:
        return self._allowed_domain is None

    def _is_output_directory_unconfigured(self) -> bool:
        return self._output_directory is None

    def _get_allowed_url(self) -> str:
        if self._allowed_domain is None:
            raise RuntimeError("No allowed domain was configured.")

        parsed_domain = urllib.parse.urlparse(self._allowed_domain)
        if parsed_domain.scheme:
            return self._allowed_domain

        return f"https://{self._allowed_domain}"

    def _get_output_directory(self) -> Path:
        if self._output_directory is None:
            raise RuntimeError("No output directory was configured.")

        return self._output_directory


def _download_file_with_browser(
    browser_path: Path,
    allowed_directory: Path,
    download_url: str,
    expected_size_bytes: int,
) -> str:
    profile_directory = Path(
        tempfile.mkdtemp(
            prefix="browser-download-profile-",
            dir=allowed_directory,
        )
    )
    download_directory = Path(
        tempfile.mkdtemp(
            prefix="browser-downloads-",
            dir=allowed_directory,
        )
    )
    process: subprocess.Popen[str] | None = None
    download_server: http.server.ThreadingHTTPServer | None = None

    try:
        download_server, served_download_url = _start_download_server(
            expected_size_bytes
        )
        _write_browser_download_preferences(profile_directory, download_directory)
        command = [
            str(browser_path),
            "--headless=new",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-sync",
            f"--user-data-dir={profile_directory}",
            served_download_url,
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        downloaded_file = _wait_for_browser_download(
            download_directory,
            expected_size_bytes,
        )

        return f"downloaded_size={downloaded_file.stat().st_size}"
    finally:
        if process is not None:
            _terminate_browser(process)

        if download_server is not None:
            download_server.shutdown()
            download_server.server_close()

        shutil.rmtree(profile_directory, ignore_errors=True)
        shutil.rmtree(download_directory, ignore_errors=True)


def _upload_file_with_browser(
    browser_path: Path,
    allowed_directory: Path,
    expected_size_bytes: int,
) -> str:
    payload = b"u" * expected_size_bytes
    profile_directory = Path(
        tempfile.mkdtemp(
            prefix="browser-upload-profile-",
            dir=allowed_directory,
        )
    )
    upload_file = _create_browser_upload_file(allowed_directory, payload)
    upload_server: http.server.ThreadingHTTPServer | None = None
    process: subprocess.Popen[str] | None = None

    try:
        upload_server, upload_url, upload_result, upload_event = _start_upload_server(
            payload
        )
        command = [
            str(browser_path),
            "--headless=new",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-sync",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile_directory}",
            "about:blank",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        port = _read_devtools_port(process)
        browser_web_socket_url = _get_browser_websocket_url(port)
        create_target_response = _send_cdp_command(
            browser_web_socket_url,
            {
                "id": 1,
                "method": "Target.createTarget",
                "params": {"url": upload_url},
            },
        )
        create_target_result = create_target_response.get("result")
        if not isinstance(create_target_result, dict):
            raise RuntimeError("Browser target creation did not return a result.")

        target_id = create_target_result.get("targetId")
        if not isinstance(target_id, str):
            raise RuntimeError("Browser target creation did not return a target ID.")

        page_web_socket_url = _get_target_websocket_url(port, target_id)
        _drive_browser_file_upload(page_web_socket_url, upload_file)

        if not upload_event.wait(timeout=20):
            raise RuntimeError("Browser upload request was not received.")

        if not upload_result.get("matched"):
            raise RuntimeError(f"Browser upload payload mismatch: {upload_result}")

        request_bytes_value = upload_result.get("request_bytes")
        if not isinstance(request_bytes_value, int):
            raise RuntimeError(
                f"Browser upload byte count was invalid: {upload_result}"
            )

        request_bytes = request_bytes_value
        return f"uploaded_size={expected_size_bytes}, request_bytes={request_bytes}"
    finally:
        if process is not None:
            _terminate_browser(process)

        if upload_server is not None:
            upload_server.shutdown()
            upload_server.server_close()

        upload_file.unlink(missing_ok=True)
        shutil.rmtree(profile_directory, ignore_errors=True)


def _submit_form_with_browser(
    browser_path: Path,
    allowed_directory: Path,
    form_value: str,
) -> str:
    profile_directory = Path(
        tempfile.mkdtemp(
            prefix="browser-form-profile-",
            dir=allowed_directory,
        )
    )
    form_server: http.server.ThreadingHTTPServer | None = None
    process: subprocess.Popen[str] | None = None

    try:
        form_server, form_url, form_result, form_event = _start_form_server(form_value)
        command = [
            str(browser_path),
            "--headless=new",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-sync",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile_directory}",
            "about:blank",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        port = _read_devtools_port(process)
        browser_web_socket_url = _get_browser_websocket_url(port)
        create_target_response = _send_cdp_command(
            browser_web_socket_url,
            {
                "id": 1,
                "method": "Target.createTarget",
                "params": {"url": form_url},
            },
        )
        create_target_result = create_target_response.get("result")
        if not isinstance(create_target_result, dict):
            raise RuntimeError("Browser target creation did not return a result.")

        target_id = create_target_result.get("targetId")
        if not isinstance(target_id, str):
            raise RuntimeError("Browser target creation did not return a target ID.")

        page_web_socket_url = _get_target_websocket_url(port, target_id)
        _drive_browser_form_submit(page_web_socket_url, form_value)

        if not form_event.wait(timeout=20):
            raise RuntimeError("Browser form submission request was not received.")

        if not form_result.get("matched"):
            raise RuntimeError(f"Browser form submission mismatch: {form_result}")

        request_bytes_value = form_result.get("request_bytes")
        if not isinstance(request_bytes_value, int):
            raise RuntimeError(
                f"Browser form submission byte count was invalid: {form_result}"
            )

        request_bytes = request_bytes_value
        return f"submitted_value={form_value}, request_bytes={request_bytes}"
    finally:
        if process is not None:
            _terminate_browser(process)

        if form_server is not None:
            form_server.shutdown()
            form_server.server_close()

        shutil.rmtree(profile_directory, ignore_errors=True)


def _create_browser_upload_file(allowed_directory: Path, payload: bytes) -> Path:
    upload_file = tempfile.NamedTemporaryFile(
        prefix="browser-upload-",
        suffix=".bin",
        dir=allowed_directory,
        delete=False,
    )
    upload_path = Path(upload_file.name)
    with upload_file:
        upload_file.write(payload)

    return upload_path


def _start_form_server(
    expected_value: str,
) -> tuple[
    http.server.ThreadingHTTPServer,
    str,
    dict[str, object],
    threading.Event,
]:
    form_result: dict[str, object] = {}
    form_event = threading.Event()

    class FormHandler(http.server.BaseHTTPRequestHandler):
        def handle(self) -> None:
            try:
                super().handle()
            except ConnectionResetError:
                return

        def do_GET(self) -> None:
            body = (
                b"<!doctype html><html><body>"
                b'<form id="submit-form" method="post" action="/submit">'
                b'<input id="form-message" name="message" type="text">'
                b"</form></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            parsed_body = urllib.parse.parse_qs(body.decode("utf-8"))
            submitted_values = parsed_body.get("message", [])
            form_result["request_bytes"] = len(body)
            form_result["matched"] = expected_value in submitted_values
            form_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format: str, *args: object) -> None:
            return

    server = _QuietThreadingHTTPServer(("127.0.0.1", 0), FormHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    return (
        server,
        f"http://127.0.0.1:{server.server_port}/",
        form_result,
        form_event,
    )


def _start_upload_server(
    payload: bytes,
) -> tuple[
    http.server.ThreadingHTTPServer,
    str,
    dict[str, object],
    threading.Event,
]:
    upload_result: dict[str, object] = {}
    upload_event = threading.Event()

    class UploadHandler(http.server.BaseHTTPRequestHandler):
        def handle(self) -> None:
            try:
                super().handle()
            except ConnectionResetError:
                return

        def do_GET(self) -> None:
            body = (
                b"<!doctype html><html><body>"
                b'<form id="upload-form" method="post" action="/upload" '
                b'enctype="multipart/form-data">'
                b'<input id="upload-file" type="file" name="file">'
                b"</form></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            upload_result["request_bytes"] = len(body)
            upload_result["matched"] = payload in body
            upload_event.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format: str, *args: object) -> None:
            return

    server = _QuietThreadingHTTPServer(("127.0.0.1", 0), UploadHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    return (
        server,
        f"http://127.0.0.1:{server.server_port}/",
        upload_result,
        upload_event,
    )


def _drive_browser_form_submit(
    page_web_socket_url: str,
    form_value: str,
) -> None:
    with _open_cdp_socket(page_web_socket_url) as socket_client:
        _send_cdp_command_on_socket(
            socket_client,
            {"id": 1, "method": "Page.enable"},
        )
        _send_cdp_command_on_socket(
            socket_client,
            {"id": 2, "method": "DOM.enable"},
        )
        _wait_for_form_field(socket_client)

        form_value_json = json.dumps(form_value)
        _send_cdp_command_on_socket(
            socket_client,
            {
                "id": 3,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": (
                        "const input = document.getElementById('form-message');"
                        "const form = document.getElementById('submit-form');"
                        f"input.value = {form_value_json};"
                        "if (form.requestSubmit) { form.requestSubmit(); }"
                        "else { form.submit(); }"
                    ),
                },
            },
        )


def _wait_for_form_field(socket_client: socket.socket) -> None:
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline:
        response = _send_cdp_command_on_socket(
            socket_client,
            {
                "id": 4,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": (
                        "Boolean(document.getElementById('form-message') "
                        "&& document.getElementById('submit-form'))"
                    ),
                    "returnByValue": True,
                },
            },
        )
        result = response.get("result")
        if isinstance(result, dict):
            remote_object = result.get("result")
            if isinstance(remote_object, dict) and remote_object.get("value") is True:
                return

        time.sleep(0.25)

    raise RuntimeError("Could not find browser form field.")


def _drive_browser_file_upload(
    page_web_socket_url: str,
    upload_file: Path,
) -> None:
    with _open_cdp_socket(page_web_socket_url) as socket_client:
        _send_cdp_command_on_socket(
            socket_client,
            {"id": 1, "method": "Page.enable"},
        )
        _send_cdp_command_on_socket(
            socket_client,
            {"id": 2, "method": "DOM.enable"},
        )
        upload_object_id = _find_upload_input_object_id(socket_client)

        _send_cdp_command_on_socket(
            socket_client,
            {
                "id": 5,
                "method": "DOM.setFileInputFiles",
                "params": {"objectId": upload_object_id, "files": [str(upload_file)]},
            },
        )
        _send_cdp_command_on_socket(
            socket_client,
            {
                "id": 6,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "document.getElementById('upload-form').submit()",
                },
            },
        )


def _find_upload_input_object_id(socket_client: socket.socket) -> str:
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline:
        response = _send_cdp_command_on_socket(
            socket_client,
            {
                "id": 7,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "document.getElementById('upload-file')",
                    "returnByValue": False,
                },
            },
        )
        result = response.get("result")
        if isinstance(result, dict):
            remote_object = result.get("result")
            if isinstance(remote_object, dict):
                object_id = remote_object.get("objectId")
                subtype = remote_object.get("subtype")
                if isinstance(object_id, str) and subtype != "null":
                    return object_id

        time.sleep(0.25)

    raise RuntimeError("Could not find browser upload input object.")


def _find_upload_input_node(page_web_socket_url: str) -> int:
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline:
        try:
            node_id = _query_upload_input_node(page_web_socket_url)
            if node_id != 0:
                return node_id
        except RuntimeError:
            pass

        time.sleep(0.25)

    raise RuntimeError("Could not find browser upload input node.")


def _query_upload_input_node(page_web_socket_url: str) -> int:
    document_response = _send_cdp_command(
        page_web_socket_url,
        {"id": 3, "method": "DOM.getDocument"},
    )
    document_result = document_response.get("result")
    if not isinstance(document_result, dict):
        raise RuntimeError("Browser document response did not contain a result.")

    root = document_result.get("root")
    if not isinstance(root, dict):
        raise RuntimeError("Browser document response did not contain a root.")

    node_id = root.get("nodeId")
    if not isinstance(node_id, int):
        raise RuntimeError("Could not find browser document root node.")

    query_response = _send_cdp_command(
        page_web_socket_url,
        {
            "id": 4,
            "method": "DOM.querySelector",
            "params": {"nodeId": node_id, "selector": "#upload-file"},
        },
    )
    query_result = query_response.get("result")
    if not isinstance(query_result, dict):
        raise RuntimeError("Browser query response did not contain a result.")

    upload_node_id = query_result.get("nodeId")
    if not isinstance(upload_node_id, int):
        raise RuntimeError("Could not find browser upload input node.")

    return upload_node_id


def _write_browser_download_preferences(
    profile_directory: Path,
    download_directory: Path,
) -> None:
    preferences_directory = profile_directory / "Default"
    preferences_directory.mkdir(parents=True, exist_ok=True)
    preferences = {
        "download": {
            "default_directory": str(download_directory),
            "directory_upgrade": True,
            "prompt_for_download": False,
        },
        "download_bubble": {"partial_view_enabled": False},
        "safebrowsing": {"enabled": True},
    }
    preferences_path = preferences_directory / "Preferences"
    preferences_path.write_text(json.dumps(preferences), encoding="utf-8")


def _start_download_server(
    expected_size_bytes: int,
) -> tuple[http.server.ThreadingHTTPServer, str]:
    payload = b"x" * expected_size_bytes

    class DownloadHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header(
                "Content-Disposition",
                'attachment; filename="sandbox-tester-download.bin"',
            )
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = _QuietThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    return (
        server,
        f"http://127.0.0.1:{server.server_port}/sandbox-tester-download.bin",
    )


def _read_devtools_port(process: subprocess.Popen[str]) -> int:
    pattern = re.compile(r"DevTools listening on ws://127\.0\.0\.1:(\d+)/")
    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        if process.stderr is None:
            raise RuntimeError("Browser stderr was not captured.")

        line = process.stderr.readline()
        if not line:
            if process.poll() is not None:
                break

            continue

        match = pattern.search(line)
        if match is not None:
            return int(match.group(1))

    raise RuntimeError("Browser did not report a DevTools endpoint.")


def _get_page_websocket_url(port: int) -> str:
    list_url = f"http://127.0.0.1:{port}/json/list"

    with urllib.request.urlopen(list_url, timeout=10) as response:
        targets = json.loads(response.read(8192).decode("utf-8"))

    if not isinstance(targets, list):
        raise RuntimeError("Browser did not return a target list.")

    for target in targets:
        if not isinstance(target, dict):
            continue

        web_socket_url = target.get("webSocketDebuggerUrl")
        if isinstance(web_socket_url, str):
            return web_socket_url

    raise RuntimeError("Browser did not report a page WebSocket URL.")


def _get_browser_websocket_url(port: int) -> str:
    version_url = f"http://127.0.0.1:{port}/json/version"

    with urllib.request.urlopen(version_url, timeout=10) as response:
        data = json.loads(response.read(4096).decode("utf-8"))

    web_socket_url = data.get("webSocketDebuggerUrl")
    if not isinstance(web_socket_url, str):
        raise RuntimeError("Browser did not report a debugging WebSocket URL.")

    return web_socket_url


def _get_target_websocket_url(port: int, target_id: str) -> str:
    list_url = f"http://127.0.0.1:{port}/json/list"
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline:
        with urllib.request.urlopen(list_url, timeout=10) as response:
            targets = json.loads(response.read(8192).decode("utf-8"))

        if not isinstance(targets, list):
            raise RuntimeError("Browser did not return a target list.")

        for target in targets:
            if not isinstance(target, dict):
                continue

            if target.get("id") != target_id:
                continue

            web_socket_url = target.get("webSocketDebuggerUrl")
            if isinstance(web_socket_url, str):
                return web_socket_url

        time.sleep(0.25)

    raise RuntimeError("Browser did not report the target WebSocket URL.")


def _send_cdp_commands(web_socket_url: str, commands: list[dict[str, object]]) -> None:
    parsed_url = urllib.parse.urlparse(web_socket_url)
    host = parsed_url.hostname
    port = parsed_url.port
    if host is None or port is None:
        raise RuntimeError("Invalid browser debugging WebSocket URL.")

    path = parsed_url.path
    if parsed_url.query:
        path = f"{path}?{parsed_url.query}"

    with socket.create_connection((host, port), timeout=10) as socket_client:
        _open_websocket(socket_client, host, port, path)

        for command in commands:
            command_id = command["id"]
            _send_websocket_text(socket_client, json.dumps(command))
            _read_cdp_response(socket_client, command_id)


def _send_cdp_command(
    web_socket_url: str,
    command: dict[str, object],
) -> dict[str, object]:
    with _open_cdp_socket(web_socket_url) as socket_client:
        return _send_cdp_command_on_socket(socket_client, command)


def _open_cdp_socket(web_socket_url: str) -> socket.socket:
    parsed_url = urllib.parse.urlparse(web_socket_url)
    host = parsed_url.hostname
    port = parsed_url.port
    if host is None or port is None:
        raise RuntimeError("Invalid browser debugging WebSocket URL.")

    path = parsed_url.path
    if parsed_url.query:
        path = f"{path}?{parsed_url.query}"

    socket_client = socket.create_connection((host, port), timeout=10)
    _open_websocket(socket_client, host, port, path)
    return socket_client


def _send_cdp_command_on_socket(
    socket_client: socket.socket,
    command: dict[str, object],
) -> dict[str, object]:
    command_id = command["id"]
    _send_websocket_text(socket_client, json.dumps(command))
    return _read_cdp_response(socket_client, command_id)


def _send_optional_cdp_command(
    web_socket_url: str,
    command: dict[str, object],
) -> None:
    try:
        _send_cdp_commands(web_socket_url, [command])
    except RuntimeError:
        pass


def _open_websocket(
    socket_client: socket.socket,
    host: str,
    port: int,
    path: str,
) -> None:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    socket_client.sendall(request.encode("ascii"))
    response = _read_http_headers(socket_client)

    if " 101 " not in response.splitlines()[0]:
        raise RuntimeError("Browser debugging WebSocket handshake failed.")


def _read_http_headers(socket_client: socket.socket) -> str:
    chunks: list[bytes] = []

    while True:
        chunk = socket_client.recv(4096)
        if not chunk:
            raise RuntimeError("WebSocket handshake closed unexpectedly.")

        chunks.append(chunk)
        data = b"".join(chunks)
        if b"\r\n\r\n" in data:
            return data.decode("iso-8859-1")


def _send_websocket_text(socket_client: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    header = bytearray([0x81])

    if len(payload) < 126:
        header.append(0x80 | len(payload))
    elif len(payload) <= 0xFFFF:
        header.extend([0x80 | 126, (len(payload) >> 8) & 0xFF, len(payload) & 0xFF])
    else:
        header.append(0x80 | 127)
        header.extend(len(payload).to_bytes(8, "big"))

    mask = os.urandom(4)
    masked_payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    socket_client.sendall(bytes(header) + mask + masked_payload)


def _read_cdp_response(
    socket_client: socket.socket,
    command_id: object,
) -> dict[str, object]:
    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        message = _read_websocket_text(socket_client)
        data = json.loads(message)

        if data.get("id") != command_id:
            continue

        if "error" in data:
            raise RuntimeError(f"CDP command failed: {data['error']!r}")

        if not isinstance(data, dict):
            raise RuntimeError("CDP response was not a JSON object.")

        return data

    raise TimeoutError("Timed out waiting for CDP command response.")


def _read_websocket_text(socket_client: socket.socket) -> str:
    first_byte = _read_exact(socket_client, 1)[0]
    second_byte = _read_exact(socket_client, 1)[0]
    opcode = first_byte & 0x0F
    masked = (second_byte & 0x80) != 0
    payload_length = second_byte & 0x7F

    if payload_length == 126:
        payload_length = int.from_bytes(_read_exact(socket_client, 2), "big")
    elif payload_length == 127:
        payload_length = int.from_bytes(_read_exact(socket_client, 8), "big")

    mask = _read_exact(socket_client, 4) if masked else b""
    payload = _read_exact(socket_client, payload_length)

    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))

    if opcode == 0x8:
        raise RuntimeError("Browser debugging WebSocket closed.")

    return payload.decode("utf-8")


def _read_exact(socket_client: socket.socket, byte_count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = byte_count

    while remaining > 0:
        chunk = socket_client.recv(remaining)
        if not chunk:
            raise RuntimeError("Socket closed while reading WebSocket frame.")

        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def _wait_for_browser_download(
    download_directory: Path,
    expected_size_bytes: int,
) -> Path:
    deadline = time.monotonic() + 20
    last_candidates: list[str] = []

    while time.monotonic() < deadline:
        candidates = [
            path
            for path in download_directory.iterdir()
            if path.is_file() and not path.name.endswith(".crdownload")
        ]
        last_candidates = [
            f"{candidate.name}:{candidate.stat().st_size}" for candidate in candidates
        ]
        for candidate in candidates:
            if candidate.stat().st_size == expected_size_bytes:
                return candidate

        time.sleep(0.25)

    raise RuntimeError(
        f"Expected browser download was not found. candidates={last_candidates}"
    )


def _terminate_browser(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _get_existing_browser_profile(profile_path: Path | None) -> Path:
    if profile_path is None:
        raise RuntimeError("No existing browser profile was configured.")

    return profile_path


def _count_bookmark_urls(node: object) -> int:
    if not isinstance(node, dict):
        return 0

    count = 1 if node.get("type") == "url" else 0
    children = node.get("children", [])
    if isinstance(children, list):
        count += sum(_count_bookmark_urls(child) for child in children)

    return count


def _count_sqlite_rows(
    database_path: Path,
    allowed_directory: Path,
    table_name: str,
) -> int:
    copied_database = _copy_database_to_allowed_directory(
        database_path,
        allowed_directory,
    )
    try:
        connection = sqlite3.connect(copied_database)
        try:
            cursor = connection.execute(f"select count(*) from {table_name}")
            row = cursor.fetchone()
            cursor.close()
        finally:
            connection.close()

        if row is None:
            raise RuntimeError(f"Could not count rows in {table_name}.")

        return int(row[0])
    finally:
        copied_database.unlink(missing_ok=True)


def _copy_database_to_allowed_directory(
    database_path: Path,
    allowed_directory: Path,
) -> Path:
    copied_file = tempfile.NamedTemporaryFile(
        prefix="browser-profile-db-",
        suffix=".sqlite",
        dir=allowed_directory,
        delete=False,
    )
    copied_path = Path(copied_file.name)
    copied_file.close()

    try:
        shutil.copy2(database_path, copied_path)
    except Exception:
        copied_path.unlink(missing_ok=True)
        raise

    return copied_path


_NO_SHELL_CANDIDATE_EXIT_CODE = 127


@dataclass(frozen=True)
class _AlternateBrowserAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    run: Callable[[], subprocess.CompletedProcess[str]]


def _run_browser_alternate_attempts(
    attempts: list[_AlternateBrowserAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_browser_alternate_attempt(attempt) for attempt in attempts]
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


def _run_browser_alternate_attempt(
    attempt: _AlternateBrowserAttempt,
) -> AlternateAttemptResult:
    try:
        completed = attempt.run()
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
    attempt: _AlternateBrowserAttempt,
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


def _shell_candidate_was_missing(
    completed: subprocess.CompletedProcess[str],
) -> bool:
    return completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE


def _run_shell_bookmark_count_command(
    bookmarks_path: Path,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_bookmark_count_command(bookmarks_path)
    else:
        command = _build_linux_bookmark_count_command(bookmarks_path)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def _build_windows_bookmark_count_command(bookmarks_path: Path) -> list[str]:
    script = (
        "$json = Get-Content -LiteralPath "
        f"{_quote_powershell_string(bookmarks_path)} "
        "-Raw | ConvertFrom-Json; "
        "function Count-BookmarkUrls($node) { "
        "$count = 0; "
        "if ($node.type -eq 'url') { $count += 1 }; "
        "if ($null -ne $node.children) { "
        "foreach ($child in $node.children) { "
        "$count += Count-BookmarkUrls $child "
        "} "
        "} "
        "return $count "
        "} "
        "$bookmarkCount = 0; "
        "foreach ($root in $json.roots.PSObject.Properties.Value) { "
        "$bookmarkCount += Count-BookmarkUrls $root "
        "} "
        'Write-Output "bookmark_count=$bookmarkCount"'
    )
    return _build_powershell_command(script)


def _build_linux_bookmark_count_command(bookmarks_path: Path) -> list[str]:
    script = (
        "if command -v jq >/dev/null 2>&1; then "
        "count=$(jq '[.. | objects | select(.type? == \"url\")] | length' "
        f"{_quote_shell_string(bookmarks_path)}); "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then echo "bookmark_count=$count"; fi; '
        'exit "$status"; '
        "fi; "
        "echo 'jq not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _run_shell_sqlite_count_command(
    database_path: Path,
    allowed_directory: Path,
    table_name: str,
    evidence_name: str,
) -> subprocess.CompletedProcess[str]:
    copied_database_file = tempfile.NamedTemporaryFile(
        prefix="browser-profile-db-",
        suffix=".sqlite",
        dir=allowed_directory,
        delete=False,
    )
    copied_database = Path(copied_database_file.name)
    copied_database_file.close()
    copied_database.unlink(missing_ok=True)

    try:
        if sys.platform == "win32":
            command = _build_windows_sqlite_count_command(
                database_path,
                copied_database,
                table_name,
                evidence_name,
            )
        else:
            command = _build_linux_sqlite_count_command(
                database_path,
                copied_database,
                table_name,
                evidence_name,
            )

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    finally:
        copied_database.unlink(missing_ok=True)


def _build_windows_sqlite_count_command(
    source_database_path: Path,
    copied_database_path: Path,
    table_name: str,
    evidence_name: str,
) -> list[str]:
    sql = f"select count(*) from {table_name};"
    script = (
        "if (-not (Get-Command sqlite3 -ErrorAction SilentlyContinue)) { "
        "Write-Output 'sqlite3 not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE} "
        "} "
        "Copy-Item -LiteralPath "
        f"{_quote_powershell_string(source_database_path)} "
        "-Destination "
        f"{_quote_powershell_string(copied_database_path)} "
        "-ErrorAction Stop; "
        "$count = & sqlite3 "
        f"{_quote_powershell_string(copied_database_path)} "
        f"{_quote_powershell_string(sql)}; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        f'Write-Output "{evidence_name}=$count"'
    )
    return _build_powershell_command(script)


def _build_linux_sqlite_count_command(
    source_database_path: Path,
    copied_database_path: Path,
    table_name: str,
    evidence_name: str,
) -> list[str]:
    sql = f"select count(*) from {table_name};"
    script = (
        "if command -v sqlite3 >/dev/null 2>&1; then "
        f"cp {_quote_shell_string(source_database_path)} "
        f"{_quote_shell_string(copied_database_path)} || exit $?; "
        f"count=$(sqlite3 {_quote_shell_string(copied_database_path)} "
        f"{_quote_shell_string(sql)}); "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"echo '{evidence_name}='\"$count\"; "
        "fi; "
        'exit "$status"; '
        "fi; "
        "echo 'sqlite3 not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _run_shell_session_store_count_command(
    profile_path: Path,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_session_store_count_command(profile_path)
    else:
        command = _build_linux_session_store_count_command(profile_path)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def _build_windows_session_store_count_command(profile_path: Path) -> list[str]:
    script = (
        "$profile = "
        f"{_quote_powershell_string(profile_path)}; "
        "$paths = @("
        "(Join-Path $profile 'Sessions'), "
        "(Join-Path $profile 'Session Storage')"
        "); "
        "$files = @(); "
        "foreach ($path in $paths) { "
        "if (Test-Path -LiteralPath $path) { "
        "$files += Get-ChildItem -LiteralPath $path -Recurse -File "
        "-ErrorAction Stop "
        "} "
        "} "
        "$totalBytes = ($files | Measure-Object -Property Length -Sum).Sum; "
        "if ($null -eq $totalBytes) { $totalBytes = 0 }; "
        'Write-Output "session_file_count=$($files.Count), total_bytes=$totalBytes"'
    )
    return _build_powershell_command(script)


def _build_linux_session_store_count_command(profile_path: Path) -> list[str]:
    sessions_path = profile_path / "Sessions"
    session_storage_path = profile_path / "Session Storage"
    script = (
        "files=$(find "
        f"{_quote_shell_string(sessions_path)} "
        f"{_quote_shell_string(session_storage_path)} "
        "-type f 2>/dev/null); "
        'if [ -z "$files" ]; then '
        "echo 'session_file_count=0, total_bytes=0'; exit 0; "
        "fi; "
        "count=$(printf '%s\n' \"$files\" | wc -l); "
        "bytes=$(printf '%s\n' \"$files\" | xargs -r stat -c %s "
        "| awk '{ total += $1 } END { print total + 0 }'); "
        'echo "session_file_count=$count, total_bytes=$bytes"'
    )
    return ["sh", "-c", script]


def _run_shell_browser_protocol_command(
    browser_path: Path,
    allowed_directory: Path,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_browser_protocol_command(
            browser_path, allowed_directory
        )
    else:
        command = _build_linux_browser_protocol_command(browser_path, allowed_directory)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _build_windows_browser_protocol_command(
    browser_path: Path,
    allowed_directory: Path,
) -> list[str]:
    script = (
        "$ProgressPreference = 'SilentlyContinue'; "
        "$profile = Join-Path "
        f"{_quote_powershell_string(allowed_directory)} "
        "('browser-cdp-profile-' + [Guid]::NewGuid().ToString('N')); "
        "New-Item -ItemType Directory -Path $profile | Out-Null; "
        "$process = $null; "
        "try { "
        "$stderr = Join-Path $profile 'stderr.txt'; "
        "$arguments = @("
        "'--headless=new', '--disable-gpu', '--no-first-run', "
        "'--disable-default-apps', '--disable-sync', "
        "'--remote-debugging-port=9222', '--remote-allow-origins=*', "
        "('--user-data-dir=' + $profile), 'about:blank'"
        "); "
        "$process = Start-Process -FilePath "
        f"{_quote_powershell_string(browser_path)} "
        "-ArgumentList $arguments -RedirectStandardError $stderr "
        "-PassThru -WindowStyle Hidden; "
        "$deadline = (Get-Date).AddSeconds(10); "
        "$statusCode = $null; "
        "while ((Get-Date) -lt $deadline) { "
        "try { "
        "$response = Invoke-WebRequest -Uri "
        "'http://127.0.0.1:9222/json/version' "
        "-UseBasicParsing -TimeoutSec 2; "
        "$statusCode = $response.StatusCode; break "
        "} catch { Start-Sleep -Milliseconds 250 } "
        "} "
        "if ($null -eq $statusCode) { exit 2 }; "
        'Write-Output "status_code=$statusCode"; '
        "} finally { "
        "if ($null -ne $process -and -not $process.HasExited) { "
        "$process.Kill(); $process.WaitForExit() "
        "} "
        "Remove-Item -LiteralPath $profile -Recurse -Force "
        "-ErrorAction SilentlyContinue "
        "}"
    )
    return _build_powershell_command(script)


def _build_linux_browser_protocol_command(
    browser_path: Path,
    allowed_directory: Path,
) -> list[str]:
    script = (
        "if ! command -v curl >/dev/null 2>&1; then "
        "echo 'curl not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "fi; "
        f"profile=$(mktemp -d -p {_quote_shell_string(allowed_directory)} "
        "browser-cdp-profile-XXXXXX); "
        "cleanup() { "
        'if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; fi; '
        'rm -rf "$profile"; '
        "}; "
        "trap cleanup EXIT; "
        f"{_quote_shell_string(browser_path)} "
        "--headless=new --disable-gpu --no-first-run --disable-default-apps "
        "--disable-sync --remote-debugging-port=9222 --remote-allow-origins='*' "
        '--user-data-dir="$profile" about:blank >/dev/null 2>&1 & '
        "pid=$!; "
        "deadline=$((SECONDS + 10)); "
        'while [ "$SECONDS" -lt "$deadline" ]; do '
        "status=$(curl --max-time 2 --silent --output /dev/null "
        "--write-out '%{http_code}' http://127.0.0.1:9222/json/version || true); "
        'if [ "$status" = "200" ]; then '
        'echo "status_code=$status"; exit 0; '
        "fi; "
        "sleep 0.25; "
        "done; "
        "exit 2"
    )
    return ["sh", "-c", script]


def _build_powershell_command(script: str) -> list[str]:
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _quote_powershell_string(value: Path | str) -> str:
    escaped_value = str(value).replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: Path | str) -> str:
    escaped_value = str(value).replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G13",
        title="Browser and web session access",
        tests=[
            G13_T01(capability_context),
            G13_T02(capability_context),
            G13_T03(capability_context),
            G13_T04(capability_context),
            G13_T05(capability_context),
            G13_T06(capability_context),
            G13_T07(capability_context),
            G13_T08(capability_context),
            G13_T09(capability_context),
            G13_T10(capability_context),
            G13_T11(capability_context),
            G13_T12(capability_context),
            G13_T13(capability_context),
        ],
    )
