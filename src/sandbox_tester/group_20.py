"""Group 20: Hardware and device access."""

from __future__ import annotations

import asyncio
import importlib
import subprocess
import uuid
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup, OperatingSystem

_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_CAMERA_FRAME_FILE_NAME = "camera-frame.jpg"
_AUDIO_SAMPLE_FILE_NAME = "microphone-sample.wav"
_AUDIO_SAMPLE_SECONDS = 1
_AUDIO_SAMPLE_RATE = 16000


@dataclass(frozen=True)
class _AlternateHardwareAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    operation: Callable[[], subprocess.CompletedProcess[str]]


class G20_T01:
    id = "T01"
    title = "Read camera availability"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_camera_availability_command,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read camera availability.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported camera availability command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read camera availability.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Shell camera availability query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell camera availability query failed.",
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
            evidence = await asyncio.to_thread(
                _read_camera_availability,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read camera availability.",
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
                summary="Python runtime camera availability query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime camera availability query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Read camera availability with platform device query",
            bypass_class="camera_device_enumeration",
            command_family=_device_query_command_family(self._operating_system),
            operation=lambda: _run_camera_availability_command(
                self._operating_system,
            ),
        )


class G20_T02:
    id = "T02"
    title = "Capture camera frame"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._allow_camera_capture = capability_context.allow_camera_capture

    async def run_shell(self) -> InvocationResult:
        if not self._allow_camera_capture:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Camera capture was not enabled in capability context.",
            )

        frame_path = _build_camera_frame_path(self._allowed_directory)
        try:
            completed = await asyncio.to_thread(
                _run_shell_camera_capture_command,
                self._operating_system,
                frame_path,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and _captured_frame_exists(frame_path):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell captured a camera frame.",
                    evidence=_capture_evidence(frame_path),
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported shell camera capture command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not capture a camera frame.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Shell camera capture timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell camera capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            frame_path.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        if not self._allow_camera_capture:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Camera capture was not enabled in capability context.",
            )

        frame_path = _build_camera_frame_path(self._allowed_directory)
        try:
            evidence = await asyncio.to_thread(
                _capture_camera_frame_with_opencv, frame_path
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime captured a camera frame.",
                evidence=evidence,
            )
        except ModuleNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="OpenCV was not available for Python camera capture.",
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
                summary="Python runtime camera capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            frame_path.unlink(missing_ok=True)

    async def run_alternates(self) -> AlternateInvocationResult:
        if not self._allow_camera_capture:
            return _hardware_alternate_not_applicable(
                "Camera capture was not enabled in capability context."
            )

        frame_path = _build_camera_frame_path(self._allowed_directory)
        return await _run_single_hardware_alternate(
            title="Capture camera frame with ffmpeg",
            bypass_class="camera_frame_capture",
            command_family="ffmpeg",
            operation=lambda: _run_camera_capture_alternate(
                self._operating_system,
                frame_path,
            ),
        )


class G20_T03:
    id = "T03"
    title = "Read microphone availability"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_microphone_availability_command,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell read microphone availability.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary=(
                        "No supported microphone availability command was available."
                    ),
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not read microphone availability.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Shell microphone availability query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell microphone availability query failed.",
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
            evidence = await asyncio.to_thread(
                _read_microphone_availability,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime read microphone availability.",
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
                summary="Python runtime microphone availability query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime microphone availability query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Read microphone availability with platform device query",
            bypass_class="microphone_device_enumeration",
            command_family=_device_query_command_family(self._operating_system),
            operation=lambda: _run_microphone_availability_command(
                self._operating_system,
            ),
        )


class G20_T04:
    id = "T04"
    title = "Capture audio sample"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system
        self._allowed_directory = capability_context.allowed_directory
        self._allow_microphone_capture = capability_context.allow_microphone_capture

    async def run_shell(self) -> InvocationResult:
        if not self._allow_microphone_capture:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Microphone capture was not enabled in capability context.",
            )

        sample_path = _build_audio_sample_path(self._allowed_directory)
        try:
            completed = await asyncio.to_thread(
                _run_shell_audio_capture_command,
                self._operating_system,
                sample_path,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and _captured_sample_exists(sample_path):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell captured an audio sample.",
                    evidence=_sample_evidence(sample_path),
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported shell audio capture command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not capture an audio sample.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Shell audio capture timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell audio capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            sample_path.unlink(missing_ok=True)

    async def run_tool(self) -> InvocationResult:
        if not self._allow_microphone_capture:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Microphone capture was not enabled in capability context.",
            )

        sample_path = _build_audio_sample_path(self._allowed_directory)
        try:
            evidence = await asyncio.to_thread(
                _capture_audio_sample_with_sounddevice,
                sample_path,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime captured an audio sample.",
                evidence=evidence,
            )
        except ModuleNotFoundError as error:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="sounddevice was not available for Python audio capture.",
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
                summary="Python runtime audio capture failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            sample_path.unlink(missing_ok=True)

    async def run_alternates(self) -> AlternateInvocationResult:
        if not self._allow_microphone_capture:
            return _hardware_alternate_not_applicable(
                "Microphone capture was not enabled in capability context."
            )

        sample_path = _build_audio_sample_path(self._allowed_directory)
        return await _run_single_hardware_alternate(
            title="Capture audio sample with ffmpeg",
            bypass_class="microphone_audio_capture",
            command_family="ffmpeg",
            operation=lambda: _run_audio_capture_alternate(
                self._operating_system,
                sample_path,
            ),
        )


class G20_T05:
    id = "T05"
    title = "Access printer list"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(
                _run_printer_list_command,
                self._operating_system,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell accessed the printer list.",
                    evidence=completed.stdout.strip()[:500],
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No supported printer listing command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not access the printer list.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Shell printer list query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell printer list query failed.",
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
            evidence = await asyncio.to_thread(
                _read_printer_list,
                self._operating_system,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime accessed the printer list.",
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
                summary="Python runtime printer list query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime printer list query failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Access printer list with platform printer query",
            bypass_class="printer_list_enumeration",
            command_family=_printer_query_command_family(self._operating_system),
            operation=lambda: _run_printer_list_command(self._operating_system),
        )


class G20_T07:
    id = "T07"
    title = "Access USB device list"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_device_visibility_shell_test(
            self._operating_system,
            _run_usb_device_list_command,
            allowed_summary="Shell accessed the USB device list.",
            denied_summary="Shell could not access the USB device list.",
            not_applicable_summary=(
                "No supported USB device listing command was available."
            ),
            timeout_summary="Shell USB device list query timed out.",
            failed_summary="Shell USB device list query failed.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_device_visibility_tool_test(
            self._operating_system,
            _read_usb_device_list,
            allowed_summary="Python runtime accessed the USB device list.",
            denied_summary="Python runtime USB device list query failed.",
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Access USB device list with platform device query",
            bypass_class="usb_device_enumeration",
            command_family=_usb_query_command_family(self._operating_system),
            operation=lambda: _run_usb_device_list_command(self._operating_system),
        )


class G20_T08:
    id = "T08"
    title = "Access serial port"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_device_visibility_shell_test(
            self._operating_system,
            _run_serial_port_list_command,
            allowed_summary="Shell accessed serial port metadata.",
            denied_summary="Shell could not access serial port metadata.",
            not_applicable_summary=(
                "No supported serial port listing command was available."
            ),
            timeout_summary="Shell serial port query timed out.",
            failed_summary="Shell serial port query failed.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_device_visibility_tool_test(
            self._operating_system,
            _read_serial_port_list,
            allowed_summary="Python runtime accessed serial port metadata.",
            denied_summary="Python runtime serial port query failed.",
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Access serial port metadata with platform device query",
            bypass_class="serial_port_enumeration",
            command_family=_serial_query_command_family(self._operating_system),
            operation=lambda: _run_serial_port_list_command(self._operating_system),
        )


class G20_T09:
    id = "T09"
    title = "Access Bluetooth device list"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_device_visibility_shell_test(
            self._operating_system,
            _run_bluetooth_device_list_command,
            allowed_summary="Shell accessed the Bluetooth device list.",
            denied_summary="Shell could not access the Bluetooth device list.",
            not_applicable_summary=(
                "No supported Bluetooth device listing command was available."
            ),
            timeout_summary="Shell Bluetooth device list query timed out.",
            failed_summary="Shell Bluetooth device list query failed.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_device_visibility_tool_test(
            self._operating_system,
            _read_bluetooth_device_list,
            allowed_summary="Python runtime accessed the Bluetooth device list.",
            denied_summary="Python runtime Bluetooth device list query failed.",
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Access Bluetooth device list with platform device query",
            bypass_class="bluetooth_device_enumeration",
            command_family=_bluetooth_query_command_family(self._operating_system),
            operation=lambda: _run_bluetooth_device_list_command(
                self._operating_system,
            ),
        )


class G20_T10:
    id = "T10"
    title = "Access GPU details"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._operating_system = capability_context.operating_system

    async def run_shell(self) -> InvocationResult:
        return await _run_device_visibility_shell_test(
            self._operating_system,
            _run_gpu_details_command,
            allowed_summary="Shell accessed GPU details.",
            denied_summary="Shell could not access GPU details.",
            not_applicable_summary="No supported GPU details command was available.",
            timeout_summary="Shell GPU details query timed out.",
            failed_summary="Shell GPU details query failed.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_device_visibility_tool_test(
            self._operating_system,
            _read_gpu_details,
            allowed_summary="Python runtime accessed GPU details.",
            denied_summary="Python runtime GPU details query failed.",
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_single_hardware_alternate(
            title="Access GPU details with platform device query",
            bypass_class="gpu_details_enumeration",
            command_family=_gpu_query_command_family(self._operating_system),
            operation=lambda: _run_gpu_details_command(self._operating_system),
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G20",
        title="Hardware and device access",
        tests=[
            G20_T01(capability_context),
            G20_T02(capability_context),
            G20_T03(capability_context),
            G20_T04(capability_context),
            G20_T05(capability_context),
            G20_T07(capability_context),
            G20_T08(capability_context),
            G20_T09(capability_context),
            G20_T10(capability_context),
        ],
    )


async def _run_single_hardware_alternate(
    title: str,
    bypass_class: str,
    command_family: str,
    operation: Callable[[], subprocess.CompletedProcess[str]],
) -> AlternateInvocationResult:
    attempt = _AlternateHardwareAttempt(
        id="A01",
        title=title,
        bypass_class=bypass_class,
        command_family=command_family,
        operation=operation,
    )
    return await asyncio.to_thread(_run_hardware_alternate_attempts, [attempt])


def _run_hardware_alternate_attempts(
    attempts: list[_AlternateHardwareAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_hardware_alternate_attempt(attempt) for attempt in attempts]
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


def _run_hardware_alternate_attempt(
    attempt: _AlternateHardwareAttempt,
) -> AlternateAttemptResult:
    try:
        completed = attempt.operation()
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
            evidence=_failure_evidence(completed, combined_output),
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
    attempt: _AlternateHardwareAttempt,
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


def _hardware_alternate_not_applicable(summary: str) -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary=summary,
        attempts=[],
    )


def _run_camera_capture_alternate(
    operating_system: OperatingSystem,
    frame_path: Path,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = _run_shell_camera_capture_command(operating_system, frame_path)
        if completed.returncode != 0:
            return completed

        if not _captured_frame_exists(frame_path):
            return subprocess.CompletedProcess(
                args=completed.args,
                returncode=1,
                stdout="",
                stderr="Camera command succeeded, but no frame was captured.",
            )

        return subprocess.CompletedProcess(
            args=completed.args,
            returncode=0,
            stdout=_capture_evidence(frame_path),
            stderr=completed.stderr,
        )
    finally:
        frame_path.unlink(missing_ok=True)


def _run_audio_capture_alternate(
    operating_system: OperatingSystem,
    sample_path: Path,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = _run_shell_audio_capture_command(operating_system, sample_path)
        if completed.returncode != 0:
            return completed

        if not _captured_sample_exists(sample_path):
            return subprocess.CompletedProcess(
                args=completed.args,
                returncode=1,
                stdout="",
                stderr="Audio command succeeded, but no sample was captured.",
            )

        return subprocess.CompletedProcess(
            args=completed.args,
            returncode=0,
            stdout=_sample_evidence(sample_path),
            stderr=completed.stderr,
        )
    finally:
        sample_path.unlink(missing_ok=True)


def _device_query_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/pnp-cim"

    return "sh/dev-sysfs"


def _printer_query_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/printer-cim"

    return "lpstat"


def _usb_query_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/pnp-cim"

    return "lsusb/sysfs"


def _serial_query_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/pnp-cim"

    return "sh/dev"


def _bluetooth_query_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/pnp-cim"

    return "bluetoothctl/sysfs"


def _gpu_query_command_family(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        return "powershell/cim"

    return "lspci/sysfs"


def _run_camera_availability_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_camera_availability_command()
    else:
        command = _build_linux_camera_availability_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_camera_availability_command() -> list[str]:
    script = (
        "$devices = @(); "
        "if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue "
        "| Where-Object { "
        "$_.Class -in @('Camera', 'Image') "
        "-or $_.FriendlyName -match 'camera|webcam|video' "
        "}); "
        "} elseif (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-CimInstance Win32_PnPEntity "
        "-ErrorAction SilentlyContinue | Where-Object { "
        "$_.PNPClass -in @('Camera', 'Image') "
        "-or $_.Name -match 'camera|webcam|video' "
        "}); "
        "} else { "
        "Write-Output 'no supported camera availability command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$sample = ($devices | Select-Object -First 5 | ForEach-Object { "
        "if ($_.FriendlyName) { $_.FriendlyName } elseif ($_.Name) { $_.Name } "
        "else { $_.InstanceId } "
        "}) -join ';'; "
        'Write-Output "camera_count=$($devices.Count), sample=[$sample]"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_camera_availability_command() -> list[str]:
    script = (
        "devices=$(find /dev -maxdepth 1 -type c -name 'video*' "
        "2>/dev/null | sort); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "camera_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _read_camera_availability(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        completed = _run_camera_availability_command(operating_system)
        if completed.returncode != 0:
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            raise OSError(_failure_evidence(completed, combined_output))

        return completed.stdout.strip()

    devices = sorted(str(path) for path in Path("/dev").glob("video*"))
    sample = ";".join(devices[:5])
    return f"camera_count={len(devices)}, sample=[{sample}]"


def _run_microphone_availability_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_microphone_availability_command()
    else:
        command = _build_linux_microphone_availability_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_microphone_availability_command() -> list[str]:
    script = (
        "$devices = @(); "
        "if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue "
        "| Where-Object { "
        "$_.Class -in @('AudioEndpoint', 'Media') "
        "-and $_.FriendlyName -match 'microphone|mic|input|array' "
        "}); "
        "} elseif (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-CimInstance Win32_PnPEntity "
        "-ErrorAction SilentlyContinue | Where-Object { "
        "$_.PNPClass -in @('AudioEndpoint', 'Media') "
        "-and $_.Name -match 'microphone|mic|input|array' "
        "}); "
        "} else { "
        "Write-Output 'no supported microphone availability command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$sample = ($devices | Select-Object -First 5 | ForEach-Object { "
        "if ($_.FriendlyName) { $_.FriendlyName } elseif ($_.Name) { $_.Name } "
        "else { $_.InstanceId } "
        "}) -join ';'; "
        'Write-Output "microphone_count=$($devices.Count), sample=[$sample]"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_microphone_availability_command() -> list[str]:
    script = (
        "if command -v arecord >/dev/null 2>&1; then "
        "devices=$(arecord -l 2>/dev/null | grep '^card ' || true); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "microphone_count=$count, sample=[$sample]"; '
        "exit 0; "
        "fi; "
        "devices=$(find /dev/snd -maxdepth 1 -type c "
        "2>/dev/null | sort || true); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "microphone_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _read_microphone_availability(operating_system: OperatingSystem) -> str:
    if operating_system == OperatingSystem.WINDOWS:
        completed = _run_microphone_availability_command(operating_system)
        if completed.returncode != 0:
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
            raise OSError(_failure_evidence(completed, combined_output))

        return completed.stdout.strip()

    sound_directory = Path("/dev/snd")
    devices = []
    if sound_directory.exists():
        devices = sorted(str(path) for path in sound_directory.iterdir())
    sample = ";".join(devices[:5])
    return f"microphone_count={len(devices)}, sample=[{sample}]"


def _run_printer_list_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_printer_list_command()
    else:
        command = _build_linux_printer_list_command()

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _build_windows_printer_list_command() -> list[str]:
    script = (
        "$printers = @(); "
        "if (Get-Command Get-Printer -ErrorAction SilentlyContinue) { "
        "$printers = @(Get-Printer -ErrorAction SilentlyContinue); "
        "} elseif (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) { "
        "$printers = @(Get-CimInstance Win32_Printer -ErrorAction SilentlyContinue); "
        "} else { "
        "Write-Output 'no supported printer listing command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$sample = ($printers | Select-Object -First 5 | ForEach-Object { "
        "if ($_.Name) { $_.Name } else { $_.DeviceID } "
        "}) -join ';'; "
        'Write-Output "printer_count=$($printers.Count), sample=[$sample]"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_printer_list_command() -> list[str]:
    script = (
        "if command -v lpstat >/dev/null 2>&1; then "
        "printers=$(lpstat -v 2>/dev/null || true); "
        'if [ -z "$printers" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$printers\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$printers\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "printer_count=$count, sample=[$sample]"; '
        "exit 0; "
        "fi; "
        "echo 'no supported printer listing command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )
    return ["sh", "-c", script]


def _read_printer_list(operating_system: OperatingSystem) -> str:
    completed = _run_printer_list_command(operating_system)
    if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
        return "printer_count=0, sample=[]"
    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    return completed.stdout.strip()


async def _run_device_visibility_shell_test(
    operating_system: OperatingSystem,
    command_runner: Callable[
        [OperatingSystem],
        subprocess.CompletedProcess[str],
    ],
    allowed_summary: str,
    denied_summary: str,
    not_applicable_summary: str,
    timeout_summary: str,
    failed_summary: str,
) -> InvocationResult:
    try:
        completed = await asyncio.to_thread(command_runner, operating_system)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=completed.stdout.strip()[:500],
            )

        if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary=not_applicable_summary,
                evidence=_failure_evidence(completed, combined_output),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
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
            summary=timeout_summary,
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=failed_summary,
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_device_visibility_tool_test(
    operating_system: OperatingSystem,
    reader: Callable[[OperatingSystem], str],
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    try:
        evidence = await asyncio.to_thread(reader, operating_system)

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
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
            summary=denied_summary,
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Tool invocation raised an exception.",
            evidence=repr(error),
        )


def _run_usb_device_list_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_usb_device_list_command()
    else:
        command = _build_linux_usb_device_list_command()

    return _run_visibility_command(command)


def _build_windows_usb_device_list_command() -> list[str]:
    script = (
        "$devices = @(); "
        "if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue "
        "| Where-Object { $_.InstanceId -like 'USB*' -or $_.Class -eq 'USB' }); "
        "} elseif (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-CimInstance Win32_PnPEntity "
        "-ErrorAction SilentlyContinue | Where-Object { "
        "$_.DeviceID -like 'USB*' -or $_.PNPClass -eq 'USB' "
        "}); "
        "} else { "
        "Write-Output 'no supported USB device listing command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$sample = ($devices | Select-Object -First 5 | ForEach-Object { "
        "if ($_.FriendlyName) { $_.FriendlyName } elseif ($_.Name) { $_.Name } "
        "else { $_.InstanceId } "
        "}) -join ';'; "
        'Write-Output "usb_device_count=$($devices.Count), sample=[$sample]"'
    )
    return _build_powershell_command(script)


def _build_linux_usb_device_list_command() -> list[str]:
    script = (
        "if command -v lsusb >/dev/null 2>&1; then "
        "devices=$(lsusb 2>/dev/null || true); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "usb_device_count=$count, sample=[$sample]"; '
        "exit 0; "
        "fi; "
        "devices=$(find /sys/bus/usb/devices -maxdepth 1 -mindepth 1 "
        "2>/dev/null | sort || true); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "usb_device_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _read_usb_device_list(operating_system: OperatingSystem) -> str:
    return _read_visibility_from_command(operating_system, _run_usb_device_list_command)


def _run_serial_port_list_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_serial_port_list_command()
    else:
        command = _build_linux_serial_port_list_command()

    return _run_visibility_command(command)


def _build_windows_serial_port_list_command() -> list[str]:
    script = (
        "$ports = @(); "
        "if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) { "
        "$ports = @(Get-PnpDevice -PresentOnly -Class Ports "
        "-ErrorAction SilentlyContinue); "
        "} elseif (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) { "
        "$ports = @(Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue); "
        "} else { "
        "Write-Output 'no supported serial port listing command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$sample = ($ports | Select-Object -First 5 | ForEach-Object { "
        "if ($_.FriendlyName) { $_.FriendlyName } elseif ($_.Name) { $_.Name } "
        "else { $_.DeviceID } "
        "}) -join ';'; "
        'Write-Output "serial_port_count=$($ports.Count), sample=[$sample]"'
    )
    return _build_powershell_command(script)


def _build_linux_serial_port_list_command() -> list[str]:
    script = (
        "ports=$(find /dev -maxdepth 1 \\( -name 'ttyS*' -o -name 'ttyUSB*' "
        "-o -name 'ttyACM*' \\) 2>/dev/null | sort); "
        'if [ -z "$ports" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$ports\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$ports\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "serial_port_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _read_serial_port_list(operating_system: OperatingSystem) -> str:
    return _read_visibility_from_command(
        operating_system,
        _run_serial_port_list_command,
    )


def _run_bluetooth_device_list_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_bluetooth_device_list_command()
    else:
        command = _build_linux_bluetooth_device_list_command()

    return _run_visibility_command(command)


def _build_windows_bluetooth_device_list_command() -> list[str]:
    script = (
        "$devices = @(); "
        "if (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-PnpDevice -PresentOnly -Class Bluetooth "
        "-ErrorAction SilentlyContinue); "
        "} elseif (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) { "
        "$devices = @(Get-CimInstance Win32_PnPEntity "
        "-ErrorAction SilentlyContinue | Where-Object { "
        "$_.PNPClass -eq 'Bluetooth' -or $_.Name -match 'Bluetooth' "
        "}); "
        "} else { "
        "Write-Output 'no supported Bluetooth device listing command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$sample = ($devices | Select-Object -First 5 | ForEach-Object { "
        "if ($_.FriendlyName) { $_.FriendlyName } elseif ($_.Name) { $_.Name } "
        "else { $_.InstanceId } "
        "}) -join ';'; "
        'Write-Output "bluetooth_device_count=$($devices.Count), sample=[$sample]"'
    )
    return _build_powershell_command(script)


def _build_linux_bluetooth_device_list_command() -> list[str]:
    script = (
        "if command -v bluetoothctl >/dev/null 2>&1; then "
        "devices=$(bluetoothctl devices 2>/dev/null || true); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "bluetooth_device_count=$count, sample=[$sample]"; '
        "exit 0; "
        "fi; "
        "devices=$(find /sys/class/bluetooth -maxdepth 1 -mindepth 1 "
        "2>/dev/null | sort || true); "
        'if [ -z "$devices" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$devices\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$devices\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "bluetooth_device_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _read_bluetooth_device_list(operating_system: OperatingSystem) -> str:
    return _read_visibility_from_command(
        operating_system,
        _run_bluetooth_device_list_command,
    )


def _run_gpu_details_command(
    operating_system: OperatingSystem,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_gpu_details_command()
    else:
        command = _build_linux_gpu_details_command()

    return _run_visibility_command(command)


def _build_windows_gpu_details_command() -> list[str]:
    script = (
        "if (-not (Get-Command Get-CimInstance -ErrorAction SilentlyContinue)) { "
        "Write-Output 'no supported GPU details command found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$gpus = @(Get-CimInstance Win32_VideoController "
        "-ErrorAction SilentlyContinue); "
        "$sample = ($gpus | Select-Object -First 5 | ForEach-Object { "
        "$adapterRam = if ($_.AdapterRAM) { $_.AdapterRAM } else { 0 }; "
        "'{0}:{1}' -f $_.Name,$adapterRam "
        "}) -join ';'; "
        'Write-Output "gpu_count=$($gpus.Count), sample=[$sample]"'
    )
    return _build_powershell_command(script)


def _build_linux_gpu_details_command() -> list[str]:
    script = (
        "if command -v lspci >/dev/null 2>&1; then "
        "gpus=$(lspci 2>/dev/null | grep -Ei 'vga|3d|display' || true); "
        'if [ -z "$gpus" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$gpus\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$gpus\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "gpu_count=$count, sample=[$sample]"; '
        "exit 0; "
        "fi; "
        "gpus=$(find /sys/class/drm -maxdepth 1 -name 'card[0-9]*' "
        "2>/dev/null | sort || true); "
        'if [ -z "$gpus" ]; then count=0; sample=""; '
        "else "
        "count=$(printf '%s\\n' \"$gpus\" | sed '/^$/d' | wc -l); "
        "sample=$(printf '%s\\n' \"$gpus\" "
        "| sed '/^$/d' | head -n 5 | paste -sd ';' -); "
        "fi; "
        'echo "gpu_count=$count, sample=[$sample]"'
    )
    return ["sh", "-c", script]


def _read_gpu_details(operating_system: OperatingSystem) -> str:
    return _read_visibility_from_command(operating_system, _run_gpu_details_command)


def _run_visibility_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=20,
        check=False,
    )


def _read_visibility_from_command(
    operating_system: OperatingSystem,
    runner: Callable[[OperatingSystem], subprocess.CompletedProcess[str]],
) -> str:
    completed = runner(operating_system)
    if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
        return "device_count=0, sample=[]"
    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    return completed.stdout.strip()


def _build_powershell_command(script: str) -> list[str]:
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _run_shell_camera_capture_command(
    operating_system: OperatingSystem,
    frame_path: Path,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_camera_capture_command(frame_path)
    else:
        command = _build_linux_camera_capture_command(frame_path)

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=30,
        check=False,
    )


def _build_windows_camera_capture_command(frame_path: Path) -> list[str]:
    script = (
        "if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { "
        "Write-Output 'ffmpeg command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$deviceOutput = & ffmpeg -hide_banner -list_devices true "
        "-f dshow -i dummy 2>&1; "
        "$deviceName = $null; "
        "for ($index = 0; $index -lt $deviceOutput.Count; $index++) { "
        "$line = [string]$deviceOutput[$index]; "
        "if ($line -match 'DirectShow video devices') { "
        "for ($inner = $index + 1; $inner -lt $deviceOutput.Count; $inner++) { "
        "$candidate = [string]$deviceOutput[$inner]; "
        "if ($candidate -match 'DirectShow audio devices') { break }; "
        'if ($candidate -match \'"([^"]+)"\') { '
        "$deviceName = $Matches[1]; break "
        "} "
        "} "
        "break "
        "} "
        "} "
        "if (-not $deviceName) { Write-Output 'camera_device_count=0'; exit 2 }; "
        f"$framePath = {_quote_powershell_string(str(frame_path))}; "
        "$inputName = 'video=' + $deviceName; "
        "& ffmpeg -hide_banner -loglevel error -y -f dshow -i $inputName "
        "-frames:v 1 $framePath; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status }; "
        "if (-not (Test-Path -LiteralPath $framePath)) { exit 3 }; "
        "$size = (Get-Item -LiteralPath $framePath).Length; "
        'Write-Output "frame_captured=True, backend=ffmpeg, bytes=$size"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_camera_capture_command(frame_path: Path) -> list[str]:
    script = (
        "if ! command -v ffmpeg >/dev/null 2>&1; then "
        "echo 'ffmpeg command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "fi; "
        "device=$(find /dev -maxdepth 1 -type c -name 'video*' "
        "2>/dev/null | sort | head -n 1); "
        'if [ -z "$device" ]; then echo "camera_device_count=0"; exit 2; fi; '
        f"frame_path={_quote_shell_string(str(frame_path))}; "
        "ffmpeg -hide_banner -loglevel error -y -f video4linux2 "
        '-i "$device" -frames:v 1 "$frame_path"; '
        "status=$?; "
        'if [ "$status" -ne 0 ]; then exit "$status"; fi; '
        '[ -f "$frame_path" ] || exit 3; '
        'size=$(wc -c < "$frame_path"); '
        'echo "frame_captured=True, backend=ffmpeg, bytes=$size"'
    )
    return ["sh", "-c", script]


def _run_shell_audio_capture_command(
    operating_system: OperatingSystem,
    sample_path: Path,
) -> subprocess.CompletedProcess[str]:
    if operating_system == OperatingSystem.WINDOWS:
        command = _build_windows_audio_capture_command(sample_path)
    else:
        command = _build_linux_audio_capture_command(sample_path)

    return subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=30,
        check=False,
    )


def _build_windows_audio_capture_command(sample_path: Path) -> list[str]:
    script = (
        "if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { "
        "Write-Output 'ffmpeg command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$deviceOutput = & ffmpeg -hide_banner -list_devices true "
        "-f dshow -i dummy 2>&1; "
        "$deviceName = $null; "
        "for ($index = 0; $index -lt $deviceOutput.Count; $index++) { "
        "$line = [string]$deviceOutput[$index]; "
        "if ($line -match 'DirectShow audio devices') { "
        "for ($inner = $index + 1; $inner -lt $deviceOutput.Count; $inner++) { "
        "$candidate = [string]$deviceOutput[$inner]; "
        'if ($candidate -match \'"([^"]+)"\') { '
        "$deviceName = $Matches[1]; break "
        "} "
        "} "
        "break "
        "} "
        "} "
        "if (-not $deviceName) { Write-Output 'microphone_count=0'; exit 2 }; "
        f"$samplePath = {_quote_powershell_string(str(sample_path))}; "
        "$inputName = 'audio=' + $deviceName; "
        "& ffmpeg -hide_banner -loglevel error -y -f dshow -i $inputName "
        f"-t {_AUDIO_SAMPLE_SECONDS} -ac 1 -ar {_AUDIO_SAMPLE_RATE} $samplePath; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status }; "
        "if (-not (Test-Path -LiteralPath $samplePath)) { exit 3 }; "
        "$size = (Get-Item -LiteralPath $samplePath).Length; "
        'Write-Output "sample_captured=True, backend=ffmpeg, bytes=$size"'
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_audio_capture_command(sample_path: Path) -> list[str]:
    script = (
        "if ! command -v ffmpeg >/dev/null 2>&1; then "
        "echo 'ffmpeg command not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "fi; "
        f"sample_path={_quote_shell_string(str(sample_path))}; "
        "if ffmpeg -hide_banner -loglevel error -y -f pulse -i default "
        f"-t {_AUDIO_SAMPLE_SECONDS} -ac 1 -ar {_AUDIO_SAMPLE_RATE} "
        '"$sample_path"; then '
        ":; "
        "elif ffmpeg -hide_banner -loglevel error -y -f alsa -i default "
        f"-t {_AUDIO_SAMPLE_SECONDS} -ac 1 -ar {_AUDIO_SAMPLE_RATE} "
        '"$sample_path"; then '
        ":; "
        "else "
        "exit 2; "
        "fi; "
        '[ -f "$sample_path" ] || exit 3; '
        'size=$(wc -c < "$sample_path"); '
        'echo "sample_captured=True, backend=ffmpeg, bytes=$size"'
    )
    return ["sh", "-c", script]


def _capture_camera_frame_with_opencv(frame_path: Path) -> str:
    cv2 = importlib.import_module("cv2")

    camera = cv2.VideoCapture(0)
    try:
        if not camera.isOpened():
            raise OSError("OpenCV could not open camera index 0.")

        ok, frame = camera.read()
        if not ok:
            raise OSError("OpenCV could not read a frame from camera index 0.")

        if not cv2.imwrite(str(frame_path), frame):
            raise OSError("OpenCV could not write the captured frame.")
    finally:
        camera.release()

    if not _captured_frame_exists(frame_path):
        raise OSError("Captured frame file was not created.")

    return _capture_evidence(frame_path)


def _capture_audio_sample_with_sounddevice(sample_path: Path) -> str:
    sounddevice = importlib.import_module("sounddevice")
    frame_count = _AUDIO_SAMPLE_SECONDS * _AUDIO_SAMPLE_RATE
    recording = sounddevice.rec(
        frame_count,
        samplerate=_AUDIO_SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sounddevice.wait()

    with wave.open(str(sample_path), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(_AUDIO_SAMPLE_RATE)
        file.writeframes(recording.tobytes())

    if not _captured_sample_exists(sample_path):
        raise OSError("Captured audio sample file was not created.")

    return _sample_evidence(sample_path)


def _build_camera_frame_path(allowed_directory: Path) -> Path:
    return allowed_directory / f"{uuid.uuid4().hex}-{_CAMERA_FRAME_FILE_NAME}"


def _build_audio_sample_path(allowed_directory: Path) -> Path:
    return allowed_directory / f"{uuid.uuid4().hex}-{_AUDIO_SAMPLE_FILE_NAME}"


def _captured_frame_exists(frame_path: Path) -> bool:
    return frame_path.is_file() and frame_path.stat().st_size > 0


def _captured_sample_exists(sample_path: Path) -> bool:
    return sample_path.is_file() and sample_path.stat().st_size > 0


def _capture_evidence(frame_path: Path) -> str:
    file_size = frame_path.stat().st_size
    return f"frame_captured=True, file={frame_path.name}, bytes={file_size}"


def _sample_evidence(sample_path: Path) -> str:
    file_size = sample_path.stat().st_size
    return f"sample_captured=True, file={sample_path.name}, bytes={file_size}"


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
