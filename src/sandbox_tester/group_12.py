"""Group 12: User interface and desktop automation."""

from __future__ import annotations

import asyncio
import ctypes
import os
import shutil
import subprocess
from ctypes import wintypes
from dataclasses import dataclass

from PIL import ImageGrab, UnidentifiedImageError

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem


class G12_T01:
    id = "T01"
    title = "Take screenshot"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell captured a screenshot.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell screenshot command was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not capture a screenshot.",
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
                summary="Shell screenshot capture timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell screenshot capture failed.",
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
            image_size = await asyncio.to_thread(self._capture_screenshot)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime captured a screenshot.",
                evidence=f"size={image_size}",
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Tool invocation was denied by runtime permissions.",
                evidence=repr(error),
            )
        except (OSError, UnidentifiedImageError) as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime screenshot capture failed.",
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
            _run_ui_alternate_attempts,
            [
                _AlternateUiAttempt(
                    id="A01",
                    title="Capture screenshot via platform shell command",
                    bypass_class="screen_capture",
                    command_family="platform/screenshot",
                    command=(
                        _build_windows_screenshot_command()
                        if os.name == "nt"
                        else _build_linux_screenshot_command()
                    ),
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if os.name == "nt":
            command = _build_windows_screenshot_command()
        else:
            command = _build_linux_screenshot_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def _capture_screenshot(self) -> tuple[int, int]:
        image = ImageGrab.grab()
        width, height = image.size

        if width <= 0 or height <= 0:
            raise RuntimeError(f"Invalid screenshot size: {image.size}")

        return (width, height)


class G12_T07:
    id = "T07"
    title = "Open application window"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell opened a temporary application window.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell application-window command was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not open a temporary application window.",
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
                summary="Shell application window operation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell application window operation failed.",
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
            evidence = await asyncio.to_thread(self._open_temporary_window)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime opened a temporary application window.",
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
                summary="Python runtime application window operation failed.",
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
            _run_ui_alternate_attempts,
            [
                _AlternateUiAttempt(
                    id="A01",
                    title="Open temporary window via platform shell command",
                    bypass_class="application_window",
                    command_family="platform/window",
                    command=(
                        _build_windows_application_window_command()
                        if os.name == "nt"
                        else _build_linux_application_window_command()
                    ),
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if os.name == "nt":
            command = _build_windows_application_window_command()
        else:
            command = _build_linux_application_window_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _open_temporary_window(self) -> str:
        import tkinter

        root = tkinter.Tk()
        try:
            root.title("Sandbox Tester")
            root.geometry("200x100+0+0")
            root.update_idletasks()
            root.update()
            return "window_created"
        finally:
            root.destroy()


class G12_T08:
    id = "T08"
    title = "Read active window title"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read the active window title.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell active-window-title command was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read the active window title.",
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
                summary="Shell active window title query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell active window title query failed.",
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
            title = await asyncio.to_thread(self._read_active_window_title)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read the active window title.",
                evidence=f"title_length={len(title)}",
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
                summary="Python runtime active window title query failed.",
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
            _run_ui_alternate_attempts,
            [
                _AlternateUiAttempt(
                    id="A01",
                    title="Read active window title via platform shell command",
                    bypass_class="window_introspection",
                    command_family="platform/window-title",
                    command=(
                        _build_windows_active_window_title_command()
                        if self._operating_system == OperatingSystem.WINDOWS
                        else _build_linux_active_window_title_command()
                    ),
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_active_window_title_command()
        else:
            command = _build_linux_active_window_title_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _read_active_window_title(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            return self._read_windows_active_window_title()

        return self._read_linux_active_window_title()

    def _read_windows_active_window_title(self) -> str:
        get_foreground_window = ctypes.windll.user32.GetForegroundWindow
        get_foreground_window.argtypes = []
        get_foreground_window.restype = wintypes.HWND

        get_window_text_length = ctypes.windll.user32.GetWindowTextLengthW
        get_window_text_length.argtypes = [wintypes.HWND]
        get_window_text_length.restype = ctypes.c_int

        get_window_text = ctypes.windll.user32.GetWindowTextW
        get_window_text.argtypes = [
            wintypes.HWND,
            wintypes.LPWSTR,
            ctypes.c_int,
        ]
        get_window_text.restype = ctypes.c_int

        window_handle = get_foreground_window()
        if window_handle == 0:
            raise OSError("No foreground window handle was returned.")

        title_length = get_window_text_length(window_handle)
        if title_length <= 0:
            raise OSError("Foreground window title was empty or unavailable.")

        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
        copied_length = get_window_text(
            window_handle,
            title_buffer,
            title_length + 1,
        )
        if copied_length <= 0:
            raise OSError("Foreground window title could not be read.")

        return title_buffer.value

    def _read_linux_active_window_title(self) -> str:
        xdotool_path = shutil.which("xdotool")
        if xdotool_path is None:
            raise FileNotFoundError("xdotool was not found.")

        completed = subprocess.run(
            [xdotool_path, "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        title = completed.stdout.strip()

        if completed.returncode != 0:
            raise OSError(completed.stderr.strip() or "xdotool failed.")

        if not title:
            raise OSError("Active window title was empty or unavailable.")

        return title


class G12_T09:
    id = "T09"
    title = "Query accessibility channel"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried an accessibility channel.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell accessibility channel query was available.",
                    evidence=combined_output[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query an accessibility channel.",
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
                summary="Shell accessibility channel query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell accessibility channel query failed.",
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
            evidence = await asyncio.to_thread(self._query_accessibility_channel)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried an accessibility channel.",
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
                summary="Python runtime accessibility channel query failed.",
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
            _run_ui_alternate_attempts,
            [
                _AlternateUiAttempt(
                    id="A01",
                    title="Query accessibility channel via platform shell command",
                    bypass_class="accessibility_channel",
                    command_family="platform/accessibility",
                    command=(
                        _build_windows_accessibility_channel_command()
                        if self._operating_system == OperatingSystem.WINDOWS
                        else _build_linux_accessibility_channel_command()
                    ),
                )
            ],
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        if self._operating_system == OperatingSystem.WINDOWS:
            command = _build_windows_accessibility_channel_command()
        else:
            command = _build_linux_accessibility_channel_command()

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _query_accessibility_channel(self) -> str:
        if self._operating_system == OperatingSystem.WINDOWS:
            ctypes.WinDLL("UIAutomationCore.dll")
            return "UIAutomationCore.dll loaded"

        at_spi_address = os.environ.get("AT_SPI_BUS_ADDRESS")
        if at_spi_address:
            return "AT_SPI_BUS_ADDRESS present"

        if shutil.which("gdbus") is not None:
            return "gdbus present"

        if shutil.which("busctl") is not None:
            return "busctl present"

        raise OSError("No accessibility channel was found.")


_NO_SHELL_CANDIDATE_EXIT_CODE = 127


@dataclass(frozen=True)
class _AlternateUiAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _run_ui_alternate_attempts(
    attempts: list[_AlternateUiAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_ui_alternate_attempt(attempt) for attempt in attempts]
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


def _run_ui_alternate_attempt(
    attempt: _AlternateUiAttempt,
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
    attempt: _AlternateUiAttempt,
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


def _build_windows_screenshot_command() -> list[str]:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bitmap = [System.Drawing.Bitmap]::new($bounds.Width, $bounds.Height); "
        "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
        "$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, "
        "$bounds.Size); "
        "$graphics.Dispose(); "
        "$bitmap.Dispose(); "
        'Write-Output "size=($($bounds.Width), $($bounds.Height))"; '
        "if ($bounds.Width -gt 0 -and $bounds.Height -gt 0) { exit 0 } "
        "else { exit 1 }"
    )
    return _build_powershell_command(script)


def _build_linux_screenshot_command() -> list[str]:
    script = (
        "path=$(mktemp --suffix=.png); "
        'cleanup() { rm -f "$path"; }; '
        "trap cleanup EXIT; "
        "if command -v gnome-screenshot >/dev/null 2>&1; then "
        'gnome-screenshot -f "$path"; status=$?; '
        'if [ "$status" -eq 0 ] && [ -s "$path" ]; then '
        'bytes=$(wc -c < "$path"); echo "bytes=$bytes"; exit 0; fi; '
        'exit "$status"; '
        "fi; "
        "if command -v import >/dev/null 2>&1; then "
        'import -window root "$path"; status=$?; '
        'if [ "$status" -eq 0 ] && [ -s "$path" ]; then '
        'bytes=$(wc -c < "$path"); echo "bytes=$bytes"; exit 0; fi; '
        'exit "$status"; '
        "fi; "
        "if command -v grim >/dev/null 2>&1; then "
        'grim "$path"; status=$?; '
        'if [ "$status" -eq 0 ] && [ -s "$path" ]; then '
        'bytes=$(wc -c < "$path"); echo "bytes=$bytes"; exit 0; fi; '
        'exit "$status"; '
        "fi; "
        "echo 'no screenshot shell command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _build_windows_application_window_command() -> list[str]:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$form = [System.Windows.Forms.Form]::new(); "
        "$form.Text = 'Sandbox Tester'; "
        "$form.Width = 200; "
        "$form.Height = 100; "
        "$form.StartPosition = 'Manual'; "
        "$form.Left = 0; "
        "$form.Top = 0; "
        "$form.Show(); "
        "[System.Windows.Forms.Application]::DoEvents(); "
        'Write-Output "window_created"; '
        "$form.Close(); "
        "$form.Dispose()"
    )
    return _build_powershell_command(script)


def _build_linux_application_window_command() -> list[str]:
    script = (
        "if command -v zenity >/dev/null 2>&1; then "
        "timeout 2 zenity --info --title='Sandbox Tester' "
        "--text='Sandbox Tester' --timeout=1 >/dev/null 2>&1; "
        "status=$?; "
        'if [ "$status" -eq 0 ] || [ "$status" -eq 5 ] '
        "|| [ \"$status\" -eq 124 ]; then echo 'window_created'; exit 0; fi; "
        'exit "$status"; '
        "fi; "
        "if command -v xmessage >/dev/null 2>&1; then "
        "timeout 2 xmessage -center 'Sandbox Tester' >/dev/null 2>&1; "
        "status=$?; "
        'if [ "$status" -eq 0 ] || [ "$status" -eq 124 ]; then '
        "echo 'window_created'; exit 0; fi; "
        'exit "$status"; '
        "fi; "
        "echo 'no application-window shell command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _build_windows_active_window_title_command() -> list[str]:
    script = (
        "Add-Type -Namespace SandboxTester -Name User32 -MemberDefinition "
        f"{_quote_powershell_string(_USER32_WINDOW_TEXT_DECLARATION)}; "
        "$handle = [SandboxTester.User32]::GetForegroundWindow(); "
        "$length = [SandboxTester.User32]::GetWindowTextLength($handle); "
        "$builder = [System.Text.StringBuilder]::new($length + 1); "
        "[void][SandboxTester.User32]::GetWindowText($handle, $builder, "
        "$builder.Capacity); "
        "$title = $builder.ToString(); "
        'Write-Output "title_length=$($title.Length)"; '
        "if ($title.Length -gt 0) { exit 0 } else { exit 1 }"
    )
    return _build_powershell_command(script)


def _build_linux_active_window_title_command() -> list[str]:
    script = (
        "if command -v xdotool >/dev/null 2>&1; then "
        "title=$(xdotool getactivewindow getwindowname); status=$?; "
        'if [ "$status" -eq 0 ] && [ -n "$title" ]; then '
        "echo title_length=${#title}; exit 0; fi; "
        'exit "$status"; '
        "fi; "
        "if command -v wmctrl >/dev/null 2>&1; then "
        "title=$(wmctrl -l | head -n 1); status=$?; "
        'if [ "$status" -eq 0 ] && [ -n "$title" ]; then '
        "echo title_length=${#title}; exit 0; fi; "
        'exit "$status"; '
        "fi; "
        "echo 'active window title shell command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _build_windows_accessibility_channel_command() -> list[str]:
    script = (
        "Add-Type -Namespace SandboxTester -Name Kernel32 -MemberDefinition "
        f"{_quote_powershell_string(_KERNEL32_LOAD_LIBRARY_DECLARATION)}; "
        "$handle = [SandboxTester.Kernel32]::LoadLibrary('UIAutomationCore.dll'); "
        "if ($handle -ne [IntPtr]::Zero) { "
        "Write-Output 'UIAutomationCore.dll loaded'; exit 0 "
        "} else { "
        "Write-Error 'UIAutomationCore.dll could not be loaded'; exit 1 "
        "}"
    )
    return _build_powershell_command(script)


def _build_linux_accessibility_channel_command() -> list[str]:
    script = (
        'if [ -n "$AT_SPI_BUS_ADDRESS" ]; then '
        'echo "AT_SPI_BUS_ADDRESS present"; exit 0; fi; '
        "if command -v gdbus >/dev/null 2>&1; then "
        'echo "gdbus present"; exit 0; fi; '
        "if command -v busctl >/dev/null 2>&1; then "
        'echo "busctl present"; exit 0; fi; '
        "echo 'accessibility channel shell command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
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


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


_USER32_WINDOW_TEXT_DECLARATION = """
[DllImport("user32.dll")]
public static extern IntPtr GetForegroundWindow();

[DllImport("user32.dll", CharSet = CharSet.Unicode)]
public static extern int GetWindowText(
    IntPtr hWnd,
    System.Text.StringBuilder text,
    int count);

[DllImport("user32.dll", CharSet = CharSet.Unicode)]
public static extern int GetWindowTextLength(IntPtr hWnd);
"""

_KERNEL32_LOAD_LIBRARY_DECLARATION = """
[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
public static extern IntPtr LoadLibrary(string lpFileName);
"""


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G12",
        title="User interface and desktop automation",
        tests=[
            G12_T01(),
            G12_T07(),
            G12_T08(capability_context),
            G12_T09(capability_context),
        ],
    )
