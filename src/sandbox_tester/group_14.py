"""Group 14: Package, dependency, and supply-chain access."""

from __future__ import annotations

import asyncio
import os
import shutil
import site
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup

_TEST_PACKAGE_SPEC = "colorama==0.4.6"
_TEST_PACKAGE_IMPORT_NAME = "colorama"
_REGISTRY_PACKAGE_NAME = "pip"
_PYPI_JSON_URL = f"https://pypi.org/pypi/{_REGISTRY_PACKAGE_NAME}/json"
_DEPENDENCY_FILE_NAMES = [
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "pdm.lock",
    "conda-lock.yml",
    "requirements.lock",
    "requirements-dev.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
]


class G14_T01:
    id = "T01"
    title = "Query package registry"

    async def run_shell(self) -> InvocationResult:
        try:
            completed = await asyncio.to_thread(self._run_shell_command)
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and _REGISTRY_PACKAGE_NAME in completed.stdout:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell queried the Python package registry.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not query the Python package registry.",
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
                summary="Shell package registry query timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell package registry query failed.",
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
            evidence = await asyncio.to_thread(self._query_registry)

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime queried the Python package registry.",
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
                summary="Python runtime package registry query timed out.",
                evidence=repr(error),
            )
        except urllib.error.URLError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not query the Python package registry.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime package registry query failed.",
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
            _run_package_alternate_attempts,
            _build_registry_query_alternate_attempts(),
        )

    def _run_shell_command(self) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-m",
            "pip",
            "index",
            "versions",
            _REGISTRY_PACKAGE_NAME,
            "--disable-pip-version-check",
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def _query_registry(self) -> str:
        with urllib.request.urlopen(_PYPI_JSON_URL, timeout=30) as response:
            status = response.status
            content_length = len(response.read(4096))

        return f"status={status}, bytes_read={content_length}"


class G14_T02:
    id = "T02"
    title = "Install package into environment"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        environment_directory = self._create_environment_directory("shell-venv-")
        try:
            completed = await asyncio.to_thread(
                self._install_into_environment,
                environment_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell installed a package into a temporary environment.",
                    evidence=f"environment={environment_directory.name}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Shell could not install a package into a temporary environment."
                ),
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
                summary="Shell package installation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell package installation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(environment_directory, ignore_errors=True)

    async def run_tool(self) -> InvocationResult:
        environment_directory = self._create_environment_directory("tool-venv-")
        try:
            completed = await asyncio.to_thread(
                self._install_into_environment,
                environment_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime installed a package into a temporary "
                        "environment."
                    ),
                    evidence=f"environment={environment_directory.name}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not install a package into a temporary "
                    "environment."
                ),
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Python runtime package installation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime package installation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(environment_directory, ignore_errors=True)

    async def run_alternates(self) -> AlternateInvocationResult:
        environment_directory = self._create_environment_directory("alternate-venv-")
        try:
            attempts = await asyncio.to_thread(
                _build_environment_install_alternate_attempts,
                environment_directory,
            )
        except subprocess.TimeoutExpired as error:
            return _environment_install_setup_failure_result(Outcome.DENIED, error)
        except (OSError, subprocess.CalledProcessError) as error:
            return _environment_install_setup_failure_result(Outcome.DENIED, error)
        except Exception as error:
            return _environment_install_setup_failure_result(Outcome.ERROR, error)
        try:
            return await asyncio.to_thread(_run_package_alternate_attempts, attempts)
        finally:
            shutil.rmtree(environment_directory, ignore_errors=True)

    def _create_environment_directory(self, prefix: str) -> Path:
        directory = tempfile.mkdtemp(prefix=prefix, dir=self._allowed_directory)
        return Path(directory)

    def _install_into_environment(
        self,
        environment_directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        create_command = [sys.executable, "-m", "venv", str(environment_directory)]
        subprocess.run(
            create_command,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        python_path = _get_venv_python_path(environment_directory)
        install_command = [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            _TEST_PACKAGE_SPEC,
        ]

        return subprocess.run(
            install_command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )


class G14_T03:
    id = "T03"
    title = "Install package globally"

    _MARKER_FILE_NAME = "sandbox_tester_global_install_probe.tmp"

    async def run_shell(self) -> InvocationResult:
        candidate_paths = self._get_candidate_paths()
        if not candidate_paths:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No global package install locations were found.",
            )

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                candidate_paths,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell probed a writable global package install location.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=("Shell could not write to a global package install location."),
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
                summary="Shell global package install probe timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell global package install probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        candidate_paths = self._get_candidate_paths()
        if not candidate_paths:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No global package install locations were found.",
            )

        try:
            writable_paths = await asyncio.to_thread(
                self._probe_candidate_paths,
                candidate_paths,
            )

            if writable_paths:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime probed a writable global package install "
                        "location."
                    ),
                    evidence=f"writable_count={len(writable_paths)}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary=(
                    "Python runtime could not write to a global package install "
                    "location."
                ),
                evidence=f"candidate_count={len(candidate_paths)}",
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
                summary="Python runtime global package install probe failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        candidate_paths = self._get_candidate_paths()
        if not candidate_paths:
            return AlternateInvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No global package install locations were found.",
                attempts=[],
            )

        return await asyncio.to_thread(
            _run_package_alternate_attempts,
            _build_global_install_probe_alternate_attempts(
                candidate_paths,
                self._MARKER_FILE_NAME,
            ),
        )

    def _run_shell_command(
        self,
        candidate_paths: list[Path],
    ) -> subprocess.CompletedProcess[str]:
        raw_paths = [str(path) for path in candidate_paths]
        python_code = (
            "from pathlib import Path; "
            "import sys; "
            f"paths = {raw_paths!r}; "
            f"marker_name = {self._MARKER_FILE_NAME!r}; "
            "writable = []; "
            "\nfor raw_path in paths:\n"
            "    path = Path(raw_path)\n"
            "    marker = path / marker_name\n"
            "    try:\n"
            "        marker.write_text('sandbox tester probe', encoding='utf-8')\n"
            "        marker.unlink(missing_ok=True)\n"
            "    except OSError:\n"
            "        marker.unlink(missing_ok=True)\n"
            "        continue\n"
            "    writable.append(str(path))\n"
            "print(f'writable_count={len(writable)}')\n"
            "sys.exit(0 if writable else 2)\n"
        )
        command = [sys.executable, "-c", python_code]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _probe_candidate_paths(self, candidate_paths: list[Path]) -> list[Path]:
        writable_paths: list[Path] = []

        # This deliberately probes the install directory permission needed for
        # global pip installs, without installing real package code.
        for path in candidate_paths:
            marker_path = path / self._MARKER_FILE_NAME
            try:
                marker_path.write_text("sandbox tester probe", encoding="utf-8")
                marker_path.unlink(missing_ok=True)
            except OSError:
                marker_path.unlink(missing_ok=True)
                continue

            writable_paths.append(path)

        return writable_paths

    def _get_candidate_paths(self) -> list[Path]:
        candidate_paths: list[Path] = []

        for raw_path in site.getsitepackages():
            path = Path(raw_path)
            if path.exists() and path.is_dir():
                candidate_paths.append(path)

        return candidate_paths


class G14_T04:
    id = "T04"
    title = "Install package locally"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        target_directory = self._create_target_directory("shell-target-")
        try:
            completed = await asyncio.to_thread(
                self._install_into_target,
                target_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and self._package_was_installed(
                target_directory
            ):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell installed a package into a local target directory.",
                    evidence=f"target={target_directory.name}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not install a package locally.",
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
                summary="Shell local package installation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell local package installation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(target_directory, ignore_errors=True)

    async def run_tool(self) -> InvocationResult:
        target_directory = self._create_target_directory("tool-target-")
        try:
            completed = await asyncio.to_thread(
                self._install_into_target,
                target_directory,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0 and self._package_was_installed(
                target_directory
            ):
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary=(
                        "Python runtime installed a package into a local target "
                        "directory."
                    ),
                    evidence=f"target={target_directory.name}",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not install a package locally.",
                evidence=_failure_evidence(completed, combined_output),
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
                summary="Python runtime local package installation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime local package installation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )
        finally:
            shutil.rmtree(target_directory, ignore_errors=True)

    async def run_alternates(self) -> AlternateInvocationResult:
        target_directory = self._create_target_directory("alternate-target-")
        try:
            return await asyncio.to_thread(
                _run_package_alternate_attempts,
                _build_local_install_alternate_attempts(target_directory),
            )
        finally:
            shutil.rmtree(target_directory, ignore_errors=True)

    def _create_target_directory(self, prefix: str) -> Path:
        directory = tempfile.mkdtemp(prefix=prefix, dir=self._allowed_directory)
        return Path(directory)

    def _install_into_target(
        self,
        target_directory: Path,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--target",
            str(target_directory),
            _TEST_PACKAGE_SPEC,
        ]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def _package_was_installed(self, target_directory: Path) -> bool:
        package_directory = target_directory / _TEST_PACKAGE_IMPORT_NAME
        return package_directory.exists()


class G14_T06:
    id = "T06"
    title = "Modify dependency lockfile"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._working_directory = capability_context.working_directory

    async def run_shell(self) -> InvocationResult:
        dependency_file = self._find_dependency_file()
        if dependency_file is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No dependency or lockfile was found.",
            )

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                dependency_file,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell modified dependency file metadata.",
                    evidence=completed.stdout.strip()[:500],
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not modify dependency file metadata.",
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
                summary="Shell dependency file metadata mutation timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell dependency file metadata mutation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        dependency_file = self._find_dependency_file()
        if dependency_file is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No dependency or lockfile was found.",
            )

        try:
            timestamp_changed = await asyncio.to_thread(
                self._touch_and_restore,
                dependency_file,
            )

            if timestamp_changed:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Python runtime modified dependency file metadata.",
                    evidence=f"path={dependency_file.name}, restored=True",
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not modify dependency file metadata.",
                evidence=f"path={dependency_file.name}, timestamp_changed=False",
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
                summary="Python runtime dependency file metadata mutation failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        dependency_file = self._find_dependency_file()
        if dependency_file is None:
            return AlternateInvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No dependency or lockfile was found.",
                attempts=[],
            )

        return await asyncio.to_thread(
            _run_package_alternate_attempts,
            _build_lockfile_metadata_alternate_attempts(dependency_file),
        )

    def _run_shell_command(
        self,
        dependency_file: Path,
    ) -> subprocess.CompletedProcess[str]:
        python_code = (
            "import os; "
            "from pathlib import Path; "
            f"path = Path({str(dependency_file)!r}); "
            "stat = path.stat(); "
            "original_atime = stat.st_atime_ns; "
            "original_mtime = stat.st_mtime_ns; "
            "changed = False; "
            "\ntry:\n"
            "    path.touch()\n"
            "    changed = path.stat().st_mtime_ns != original_mtime\n"
            "finally:\n"
            "    os.utime(path, ns=(original_atime, original_mtime))\n"
            "print("
            "f'path={path.name}, timestamp_changed={changed}, restored=True'"
            ")\n"
            "raise SystemExit(0 if changed else 2)\n"
        )
        command = [sys.executable, "-c", python_code]

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _touch_and_restore(self, dependency_file: Path) -> bool:
        stat = dependency_file.stat()
        original_atime = stat.st_atime_ns
        original_mtime = stat.st_mtime_ns

        try:
            dependency_file.touch()
            changed_mtime = dependency_file.stat().st_mtime_ns
            return changed_mtime != original_mtime
        finally:
            os.utime(dependency_file, ns=(original_atime, original_mtime))

    def _find_dependency_file(self) -> Path | None:
        for file_name in _DEPENDENCY_FILE_NAMES:
            path = self._working_directory / file_name
            if path.exists() and path.is_file():
                return path

        return None


class G14_T07:
    id = "T07"
    title = "Read package manager credentials"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._runtime_user_directory = capability_context.runtime_user_directory

    async def run_shell(self) -> InvocationResult:
        candidate_paths = self._get_candidate_paths()
        if not candidate_paths:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No package manager credential files were found.",
            )

        try:
            completed = await asyncio.to_thread(
                self._run_shell_command,
                candidate_paths,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell inspected package manager credential locations.",
                    evidence=_credential_readability_evidence(completed.stdout),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not inspect package manager credential locations.",
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
                summary="Shell package credential inspection timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell package credential inspection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        candidate_paths = self._get_candidate_paths()
        if not candidate_paths:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No package manager credential files were found.",
            )

        try:
            evidence = await asyncio.to_thread(
                self._inspect_credential_locations,
                candidate_paths,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=(
                    "Python runtime inspected package manager credential locations."
                ),
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
                summary="Python runtime package credential inspection failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Tool invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        candidate_paths = self._get_candidate_paths()
        if not candidate_paths:
            return AlternateInvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No package manager credential files were found.",
                attempts=[],
            )

        return await asyncio.to_thread(
            _run_package_alternate_attempts,
            _build_credential_read_alternate_attempts(candidate_paths),
        )

    def _run_shell_command(
        self,
        candidate_paths: list[Path],
    ) -> subprocess.CompletedProcess[str]:
        if sys.platform == "win32":
            command = self._build_windows_read_command(candidate_paths)
        else:
            command = self._build_linux_read_command(candidate_paths)

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def _inspect_credential_locations(self, candidate_paths: list[Path]) -> str:
        readable_names: list[str] = []
        unreadable_names: list[str] = []

        for path in candidate_paths:
            try:
                with path.open("rb") as file:
                    file.read(1)
            except OSError:
                unreadable_names.append(path.name)
                continue

            readable_names.append(path.name)

        return _format_readability_evidence(readable_names, unreadable_names)

    def _get_candidate_paths(self) -> list[Path]:
        paths = self._get_pip_config_paths()
        pypirc_path = self._runtime_user_directory / ".pypirc"
        if pypirc_path.exists() and pypirc_path.is_file():
            paths.append(pypirc_path)

        return _deduplicate_paths(paths)

    def _get_pip_config_paths(self) -> list[Path]:
        command = [sys.executable, "-m", "pip", "config", "debug"]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (PermissionError, subprocess.TimeoutExpired, OSError):
            return []

        if completed.returncode != 0:
            return []

        paths: list[Path] = []
        for line in completed.stdout.splitlines():
            if ", exists:" not in line:
                continue

            raw_path, raw_exists = line.rsplit(", exists:", maxsplit=1)
            if raw_exists.strip() != "True":
                continue

            path = Path(raw_path.strip())
            if path.exists() and path.is_file():
                paths.append(path)

        return paths

    def _build_windows_read_command(self, candidate_paths: list[Path]) -> list[str]:
        powershell_paths = ", ".join(
            _quote_powershell_string(path) for path in candidate_paths
        )
        script = (
            "$readable = @(); "
            "$unreadable = @(); "
            f"$paths = @({powershell_paths}); "
            "foreach ($path in $paths) { "
            "try { "
            "Get-Content -LiteralPath $path -TotalCount 1 -ErrorAction Stop "
            "| Out-Null; "
            "$readable += [System.IO.Path]::GetFileName($path); "
            "} catch { "
            "$unreadable += [System.IO.Path]::GetFileName($path); "
            "} "
            "} "
            "$readableText = $readable -join ','; "
            "$unreadableText = $unreadable -join ','; "
            'Write-Output "readable=[$readableText], unreadable=[$unreadableText]"'
        )

        return [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]

    def _build_linux_read_command(self, candidate_paths: list[Path]) -> list[str]:
        shell_paths = " ".join(_quote_shell_string(path) for path in candidate_paths)
        script = (
            "readable=''; "
            "unreadable=''; "
            f"for path in {shell_paths}; do "
            'name=$(basename "$path"); '
            'if head -c 1 "$path" >/dev/null 2>&1; then '
            "readable=${readable:+$readable,}$name; "
            "else "
            "unreadable=${unreadable:+$unreadable,}$name; "
            "fi; "
            "done; "
            'printf \'readable=[%s], unreadable=[%s]\\n\' "$readable" "$unreadable"'
        )

        return ["sh", "-c", script]


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G14",
        title="Package, dependency, and supply-chain access",
        tests=[
            G14_T01(),
            G14_T02(capability_context),
            G14_T03(),
            G14_T04(capability_context),
            G14_T06(capability_context),
            G14_T07(capability_context),
        ],
    )


@dataclass(frozen=True)
class _AlternatePackageAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    command: list[str]


def _build_registry_query_alternate_attempts() -> list[_AlternatePackageAttempt]:
    if sys.platform == "win32":
        return [
            _AlternatePackageAttempt(
                id="A01",
                title="Query package registry via PowerShell WebRequest",
                bypass_class="alternate_command",
                command_family="powershell/WebRequest",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$ErrorActionPreference = 'Stop'; "
                        f"$request = [System.Net.WebRequest]::Create("
                        f"{_quote_powershell_string(_PYPI_JSON_URL)}); "
                        "$request.Timeout = 30000; "
                        "$response = $request.GetResponse(); "
                        "Write-Output ('status=' + [int]$response.StatusCode); "
                        "$response.Close()"
                    ),
                ],
            )
        ]

    return [
        _AlternatePackageAttempt(
            id="A01",
            title="Query package registry via curl",
            bypass_class="alternate_command",
            command_family="curl",
            command=["curl", "--max-time", "30", "--silent", "--head", _PYPI_JSON_URL],
        ),
        _AlternatePackageAttempt(
            id="A02",
            title="Query package registry via wget",
            bypass_class="alternate_command",
            command_family="wget",
            command=["wget", "--spider", "--timeout=30", _PYPI_JSON_URL],
        ),
    ]


def _build_environment_install_alternate_attempts(
    environment_directory: Path,
) -> list[_AlternatePackageAttempt]:
    create_command = [sys.executable, "-m", "venv", str(environment_directory)]
    subprocess.run(
        create_command,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )

    pip_path = _get_venv_pip_path(environment_directory)
    return [
        _AlternatePackageAttempt(
            id="A01",
            title="Install package into environment via pip executable",
            bypass_class="alternate_command",
            command_family="pip",
            command=[
                str(pip_path),
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--index-url",
                "https://pypi.org/simple",
                _TEST_PACKAGE_SPEC,
            ],
        )
    ]


def _build_global_install_probe_alternate_attempts(
    candidate_paths: list[Path],
    marker_file_name: str,
) -> list[_AlternatePackageAttempt]:
    if sys.platform == "win32":
        commands = []
        for path in candidate_paths:
            marker = path / marker_file_name
            quoted_marker = _quote_powershell_string(marker)
            commands.append(
                "try { "
                f"Set-Content -LiteralPath {quoted_marker} "
                "-Value 'sandbox tester probe' -ErrorAction Stop; "
                f"Remove-Item -LiteralPath {quoted_marker} -Force; "
                f"Write-Output 'writable={path}'; exit 0 "
                "} catch { "
                f"Remove-Item -LiteralPath {quoted_marker} "
                "-Force -ErrorAction SilentlyContinue "
                "}"
            )
        script = "; ".join(commands) + "; exit 2"
        return [
            _AlternatePackageAttempt(
                id="A01",
                title="Probe global install path via PowerShell file write",
                bypass_class="alternate_command",
                command_family="powershell/file-write",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
            )
        ]

    path_arguments = " ".join(_quote_shell_string(path) for path in candidate_paths)
    marker_name = _quote_shell_string(marker_file_name)
    script = (
        f"marker_name={marker_name}; "
        f"for path in {path_arguments}; do "
        'marker="$path/$marker_name"; '
        'if printf "%s" "sandbox tester probe" > "$marker" 2>/dev/null; then '
        'rm -f "$marker"; '
        'printf "writable=%s\\n" "$path"; '
        "exit 0; "
        "fi; "
        'rm -f "$marker" 2>/dev/null; '
        "done; "
        "exit 2"
    )
    return [
        _AlternatePackageAttempt(
            id="A01",
            title="Probe global install path via shell file write",
            bypass_class="alternate_command",
            command_family="sh/file-write",
            command=["sh", "-c", script],
        )
    ]


def _build_local_install_alternate_attempts(
    target_directory: Path,
) -> list[_AlternatePackageAttempt]:
    return [
        _AlternatePackageAttempt(
            id="A01",
            title="Install package locally via pip executable",
            bypass_class="alternate_command",
            command_family="pip",
            command=[
                _get_pip_executable_name(),
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--index-url",
                "https://pypi.org/simple",
                "--target",
                str(target_directory),
                _TEST_PACKAGE_SPEC,
            ],
        )
    ]


def _build_lockfile_metadata_alternate_attempts(
    dependency_file: Path,
) -> list[_AlternatePackageAttempt]:
    if sys.platform == "win32":
        quoted_path = _quote_powershell_string(dependency_file)
        script = (
            "$ErrorActionPreference = 'Stop'; "
            f"$path = {quoted_path}; "
            "$item = Get-Item -LiteralPath $path; "
            "$originalAccess = $item.LastAccessTimeUtc; "
            "$originalWrite = $item.LastWriteTimeUtc; "
            "$item.LastWriteTimeUtc = [DateTime]::UtcNow; "
            "$changed = (Get-Item -LiteralPath $path).LastWriteTimeUtc "
            "-ne $originalWrite; "
            "$item = Get-Item -LiteralPath $path; "
            "$item.LastAccessTimeUtc = $originalAccess; "
            "$item.LastWriteTimeUtc = $originalWrite; "
            "Write-Output ('timestamp_changed=' + $changed); "
            "if (-not $changed) { exit 2 }"
        )
        return [
            _AlternatePackageAttempt(
                id="A01",
                title="Modify dependency file metadata via PowerShell",
                bypass_class="alternate_command",
                command_family="powershell/timestamp",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
            )
        ]

    quoted_path = _quote_shell_string(dependency_file)
    script = (
        f"path={quoted_path}; "
        "stamp=$(mktemp); "
        'touch -r "$path" "$stamp"; '
        'touch "$path"; '
        "changed=yes; "
        'touch -r "$stamp" "$path"; '
        'rm -f "$stamp"; '
        'printf "timestamp_changed=%s, restored=True\\n" "$changed"'
    )
    return [
        _AlternatePackageAttempt(
            id="A01",
            title="Modify dependency file metadata via touch",
            bypass_class="alternate_command",
            command_family="touch",
            command=["sh", "-c", script],
        )
    ]


def _build_credential_read_alternate_attempts(
    candidate_paths: list[Path],
) -> list[_AlternatePackageAttempt]:
    if sys.platform == "win32":
        commands = []
        for path in candidate_paths:
            quoted_path = _quote_powershell_string(path)
            commands.append(
                "try { "
                "$stream = [System.IO.File]::OpenRead("
                f"{quoted_path}); "
                "$stream.Close(); "
                f"Write-Output 'readable={path.name}' "
                "} catch { "
                f"Write-Output 'unreadable={path.name}' "
                "}"
            )
        return [
            _AlternatePackageAttempt(
                id="A01",
                title="Read credential file handles via PowerShell",
                bypass_class="alternate_command",
                command_family="powershell/File.OpenRead",
                command=[
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "; ".join(commands),
                ],
            )
        ]

    path_arguments = " ".join(_quote_shell_string(path) for path in candidate_paths)
    script = (
        f"for path in {path_arguments}; do "
        'name=$(basename "$path"); '
        'if dd if="$path" of=/dev/null bs=1 count=1 >/dev/null 2>&1; then '
        'printf "readable=%s\\n" "$name"; '
        "else "
        'printf "unreadable=%s\\n" "$name"; '
        "fi; "
        "done"
    )
    return [
        _AlternatePackageAttempt(
            id="A01",
            title="Read credential file bytes via dd",
            bypass_class="alternate_command",
            command_family="dd",
            command=["sh", "-c", script],
        )
    ]


def _run_package_alternate_attempts(
    attempts: list[_AlternatePackageAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_package_alternate_attempt(attempt) for attempt in attempts]
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


def _run_package_alternate_attempt(
    attempt: _AlternatePackageAttempt,
) -> AlternateAttemptResult:
    try:
        completed = subprocess.run(
            attempt.command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=120,
            check=False,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        if completed.returncode == 0:
            outcome = Outcome.ALLOWED
        elif completed.returncode == 127:
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
    attempt: _AlternatePackageAttempt,
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


def _environment_install_setup_failure_result(
    outcome: Outcome,
    error: Exception,
) -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=outcome,
        summary="No alternate shell attempts succeeded.",
        attempts=[
            AlternateAttemptResult(
                id="A01",
                title="Create package installation virtual environment",
                outcome=outcome,
                bypass_class="alternate_command",
                command_family="python/venv",
                evidence=_environment_install_setup_failure_evidence(error),
            )
        ],
    )


def _environment_install_setup_failure_evidence(error: Exception) -> str:
    if not isinstance(error, subprocess.CalledProcessError):
        return repr(error)

    output = "\n".join(
        part
        for part in (str(error.stdout or "").strip(), str(error.stderr or "").strip())
        if part
    )
    if output:
        return output[:500]

    return repr(error)


def _get_venv_python_path(environment_directory: Path) -> Path:
    if sys.platform == "win32":
        return environment_directory / "Scripts" / "python.exe"

    return environment_directory / "bin" / "python"


def _get_venv_pip_path(environment_directory: Path) -> Path:
    if sys.platform == "win32":
        return environment_directory / "Scripts" / "pip.exe"

    return environment_directory / "bin" / "pip"


def _get_pip_executable_name() -> str:
    if sys.platform == "win32":
        return "pip.exe"

    return "pip"


def _deduplicate_paths(paths: list[Path]) -> list[Path]:
    deduplicated_paths: list[Path] = []
    seen_paths: set[str] = set()

    for path in paths:
        path_key = str(path).casefold() if sys.platform == "win32" else str(path)
        if path_key in seen_paths:
            continue

        seen_paths.add(path_key)
        deduplicated_paths.append(path)

    return deduplicated_paths


def _format_readability_evidence(
    readable_names: list[str],
    unreadable_names: list[str],
) -> str:
    readable_text = ",".join(readable_names)
    unreadable_text = ",".join(unreadable_names)

    return f"readable=[{readable_text}], unreadable=[{unreadable_text}]"


def _credential_readability_evidence(output: str) -> str:
    readable_names: list[str] = []
    unreadable_names: list[str] = []

    for line in output.splitlines():
        if line.startswith("readable="):
            readable_names.append(line.split("=", 1)[1])
        elif line.startswith("unreadable="):
            unreadable_names.append(line.split("=", 1)[1])

    return _format_readability_evidence(readable_names, unreadable_names)


def _quote_powershell_string(value: str | Path) -> str:
    escaped_value = str(value).replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str | Path) -> str:
    escaped_value = str(value).replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
