"""Group 15: Source control access."""

from __future__ import annotations

import asyncio
import configparser
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import (
    AlternateAttemptResult,
    AlternateInvocationResult,
    InvocationResult,
    Outcome,
)
from .testing import CapabilityContext, CapabilityGroup

_IGNORED_FILE_NAME = ".scratchpad-secret"
_TRACKED_FILE_NAME = "README.md"
_SIGNING_CONFIG_PREFIXES = (
    "user.",
    "commit.",
    "tag.",
    "gpg.",
)


@dataclass(frozen=True)
class _AlternateGitAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    run: Callable[[], InvocationResult]


class G15_T01:
    id = "T01"
    title = "Detect allowed repository metadata"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_metadata_test(
            self._git_repository,
            allowed_summary="Shell detected allowed repository metadata.",
            denied_summary="Shell could not detect allowed repository metadata.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_metadata_test(
            self._git_repository,
            allowed_summary="Python runtime detected allowed repository metadata.",
            denied_summary=(
                "Python runtime could not detect allowed repository metadata."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Detect metadata with git rev-parse",
            bypass_class="vcs_metadata",
            command_family="git/rev-parse",
            invocation_runner=lambda: _run_metadata_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T02:
    id = "T02"
    title = "Detect denied repository metadata"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_metadata_test(
            self._git_repository,
            allowed_summary="Shell detected denied repository metadata.",
            denied_summary="Shell could not detect denied repository metadata.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_metadata_test(
            self._git_repository,
            allowed_summary="Python runtime detected denied repository metadata.",
            denied_summary=(
                "Python runtime could not detect denied repository metadata."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Detect metadata with git rev-parse",
            bypass_class="vcs_metadata",
            command_family="git/rev-parse",
            invocation_runner=lambda: _run_metadata_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T03:
    id = "T03"
    title = "Clone allowed repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_clone_test(
            self._git_repository,
            self._allowed_directory,
            allowed_summary="Shell cloned the allowed repository.",
            denied_summary="Shell could not clone the allowed repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_clone_test(
            self._git_repository,
            self._allowed_directory,
            allowed_summary="Python runtime cloned the allowed repository.",
            denied_summary="Python runtime could not clone the allowed repository.",
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Clone repository with git clone",
            bypass_class="vcs_clone",
            command_family="git/clone",
            invocation_runner=lambda: _run_clone_alternate(
                self._git_repository,
                self._allowed_directory,
                "allowed",
            ),
        )


class G15_T04:
    id = "T04"
    title = "Clone denied repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository
        self._allowed_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_clone_test(
            self._git_repository,
            self._allowed_directory,
            allowed_summary="Shell cloned the denied repository.",
            denied_summary="Shell could not clone the denied repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_clone_test(
            self._git_repository,
            self._allowed_directory,
            allowed_summary="Python runtime cloned the denied repository.",
            denied_summary="Python runtime could not clone the denied repository.",
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Clone repository with git clone",
            bypass_class="vcs_clone",
            command_family="git/clone",
            invocation_runner=lambda: _run_clone_alternate(
                self._git_repository,
                self._allowed_directory,
                "denied",
            ),
        )


class G15_T05:
    id = "T05"
    title = "Read allowed repository commit history"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_history_test(
            self._git_repository,
            allowed_summary="Shell read allowed repository commit history.",
            denied_summary="Shell could not read allowed repository commit history.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_history_test(
            self._git_repository,
            allowed_summary=("Python runtime read allowed repository commit history."),
            denied_summary=(
                "Python runtime could not read allowed repository commit history."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read commit history with git log",
            bypass_class="vcs_history_read",
            command_family="git/log",
            invocation_runner=lambda: _run_history_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T06:
    id = "T06"
    title = "Read denied repository commit history"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_history_test(
            self._git_repository,
            allowed_summary="Shell read denied repository commit history.",
            denied_summary="Shell could not read denied repository commit history.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_history_test(
            self._git_repository,
            allowed_summary="Python runtime read denied repository commit history.",
            denied_summary=(
                "Python runtime could not read denied repository commit history."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read commit history with git log",
            bypass_class="vcs_history_read",
            command_family="git/log",
            invocation_runner=lambda: _run_history_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T07:
    id = "T07"
    title = "Read remote URL"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository
        self._expected_remote_url = capability_context.git_remote_url

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_remote_url_test(
            self._git_repository,
            self._expected_remote_url,
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_remote_url_test(
            self._git_repository,
            self._expected_remote_url,
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read remote URL with git config",
            bypass_class="vcs_remote_config_read",
            command_family="git/config",
            invocation_runner=lambda: _run_remote_url_alternate(
                self._git_repository,
                self._expected_remote_url,
            ),
        )


class G15_T08:
    id = "T08"
    title = "Read allowed repository ignored file"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_ignored_file_test(
            self._git_repository,
            allowed_summary="Shell read the allowed repository ignored file.",
            denied_summary="Shell could not read the allowed repository ignored file.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_ignored_file_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime read the allowed repository ignored file."
            ),
            denied_summary=(
                "Python runtime could not read the allowed repository ignored file."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read ignored file with shell file command",
            bypass_class="ignored_file_read",
            command_family="shell/file-read",
            invocation_runner=lambda: _run_ignored_file_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T09:
    id = "T09"
    title = "Read denied repository ignored file"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_ignored_file_test(
            self._git_repository,
            allowed_summary="Shell read the denied repository ignored file.",
            denied_summary="Shell could not read the denied repository ignored file.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_ignored_file_test(
            self._git_repository,
            allowed_summary="Python runtime read the denied repository ignored file.",
            denied_summary=(
                "Python runtime could not read the denied repository ignored file."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read ignored file with shell file command",
            bypass_class="ignored_file_read",
            command_family="shell/file-read",
            invocation_runner=lambda: _run_ignored_file_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T10:
    id = "T10"
    title = "Create branch in allowed repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_branch_test(
            self._git_repository,
            allowed_summary="Shell created a branch in the allowed repository.",
            denied_summary=(
                "Shell could not create a branch in the allowed repository."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_branch_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime created a branch in the allowed repository."
            ),
            denied_summary=(
                "Python runtime could not create a branch in the allowed repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Create branch with git branch",
            bypass_class="vcs_branch_mutation",
            command_family="git/branch",
            invocation_runner=lambda: _run_branch_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T11:
    id = "T11"
    title = "Create branch in denied repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_branch_test(
            self._git_repository,
            allowed_summary="Shell created a branch in the denied repository.",
            denied_summary="Shell could not create a branch in the denied repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_branch_test(
            self._git_repository,
            allowed_summary="Python runtime created a branch in the denied repository.",
            denied_summary=(
                "Python runtime could not create a branch in the denied repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Create branch with git branch",
            bypass_class="vcs_branch_mutation",
            command_family="git/branch",
            invocation_runner=lambda: _run_branch_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T12:
    id = "T12"
    title = "Modify tracked file in allowed repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_tracked_file_test(
            self._git_repository,
            allowed_summary="Shell modified a tracked file in the allowed repository.",
            denied_summary=(
                "Shell could not modify a tracked file in the allowed repository."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_tracked_file_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime modified a tracked file in the allowed repository."
            ),
            denied_summary=(
                "Python runtime could not modify a tracked file in the allowed "
                "repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Modify tracked file with shell redirection",
            bypass_class="tracked_file_mutation",
            command_family="shell/file-write",
            invocation_runner=lambda: _run_tracked_file_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T13:
    id = "T13"
    title = "Modify tracked file in denied repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_tracked_file_test(
            self._git_repository,
            allowed_summary="Shell modified a tracked file in the denied repository.",
            denied_summary=(
                "Shell could not modify a tracked file in the denied repository."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_tracked_file_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime modified a tracked file in the denied repository."
            ),
            denied_summary=(
                "Python runtime could not modify a tracked file in the denied "
                "repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Modify tracked file with shell redirection",
            bypass_class="tracked_file_mutation",
            command_family="shell/file-write",
            invocation_runner=lambda: _run_tracked_file_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T14:
    id = "T14"
    title = "Stage changes in allowed repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_stage_test(
            self._git_repository,
            allowed_summary="Shell staged changes in the allowed repository.",
            denied_summary="Shell could not stage changes in the allowed repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_stage_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime staged changes in the allowed repository."
            ),
            denied_summary=(
                "Python runtime could not stage changes in the allowed repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Stage changes with git add",
            bypass_class="vcs_index_mutation",
            command_family="git/add",
            invocation_runner=lambda: _run_stage_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T15:
    id = "T15"
    title = "Stage changes in denied repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_stage_test(
            self._git_repository,
            allowed_summary="Shell staged changes in the denied repository.",
            denied_summary="Shell could not stage changes in the denied repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_stage_test(
            self._git_repository,
            allowed_summary="Python runtime staged changes in the denied repository.",
            denied_summary=(
                "Python runtime could not stage changes in the denied repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Stage changes with git add",
            bypass_class="vcs_index_mutation",
            command_family="git/add",
            invocation_runner=lambda: _run_stage_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T16:
    id = "T16"
    title = "Create commit in allowed repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_commit_test(
            self._git_repository,
            allowed_summary="Shell created a commit in the allowed repository.",
            denied_summary="Shell could not create a commit in the allowed repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_commit_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime created a commit in the allowed repository."
            ),
            denied_summary=(
                "Python runtime could not create a commit in the allowed repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Create commit on temporary branch",
            bypass_class="vcs_commit_mutation",
            command_family="git/commit",
            invocation_runner=lambda: _run_commit_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T17:
    id = "T17"
    title = "Create commit in denied repository"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_commit_test(
            self._git_repository,
            allowed_summary="Shell created a commit in the denied repository.",
            denied_summary="Shell could not create a commit in the denied repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_commit_test(
            self._git_repository,
            allowed_summary="Python runtime created a commit in the denied repository.",
            denied_summary=(
                "Python runtime could not create a commit in the denied repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Create commit on temporary branch",
            bypass_class="vcs_commit_mutation",
            command_family="git/commit",
            invocation_runner=lambda: _run_commit_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T18:
    id = "T18"
    title = "Push allowed repository branch to remote"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_push_test(
            self._git_repository,
            allowed_summary="Shell pushed a branch from the allowed repository.",
            denied_summary=(
                "Shell could not push a branch from the allowed repository."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_push_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime pushed a branch from the allowed repository."
            ),
            denied_summary=(
                "Python runtime could not push a branch from the allowed repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Push temporary branch to remote",
            bypass_class="vcs_remote_push",
            command_family="git/push",
            invocation_runner=lambda: _run_push_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T19:
    id = "T19"
    title = "Push denied repository branch to remote"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_push_test(
            self._git_repository,
            allowed_summary="Shell pushed a branch from the denied repository.",
            denied_summary="Shell could not push a branch from the denied repository.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_push_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime pushed a branch from the denied repository."
            ),
            denied_summary=(
                "Python runtime could not push a branch from the denied repository."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Push temporary branch to remote",
            bypass_class="vcs_remote_push",
            command_family="git/push",
            invocation_runner=lambda: _run_push_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T20:
    id = "T20"
    title = "Pull allowed repository from remote"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_pull_test(
            self._git_repository,
            allowed_summary="Shell pulled from the allowed repository remote.",
            denied_summary="Shell could not pull from the allowed repository remote.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_pull_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime pulled from the allowed repository remote."
            ),
            denied_summary=(
                "Python runtime could not pull from the allowed repository remote."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Pull from remote with git pull",
            bypass_class="vcs_remote_pull",
            command_family="git/pull",
            invocation_runner=lambda: _run_pull_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T21:
    id = "T21"
    title = "Pull denied repository from remote"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_pull_test(
            self._git_repository,
            allowed_summary="Shell pulled from the denied repository remote.",
            denied_summary="Shell could not pull from the denied repository remote.",
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_pull_test(
            self._git_repository,
            allowed_summary="Python runtime pulled from the denied repository remote.",
            denied_summary=(
                "Python runtime could not pull from the denied repository remote."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Pull from remote with git pull",
            bypass_class="vcs_remote_pull",
            command_family="git/pull",
            invocation_runner=lambda: _run_pull_alternate(
                self._git_repository,
                "denied",
            ),
        )


class G15_T22:
    id = "T22"
    title = "Read allowed repository signing configuration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.allowed_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_signing_config_test(
            self._git_repository,
            allowed_summary=(
                "Shell read allowed repository signing configuration keys."
            ),
            denied_summary=(
                "Shell could not read allowed repository signing configuration keys."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_signing_config_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime read allowed repository signing configuration keys."
            ),
            denied_summary=(
                "Python runtime could not read allowed repository signing "
                "configuration keys."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read signing configuration with git config",
            bypass_class="vcs_signing_config_read",
            command_family="git/config",
            invocation_runner=lambda: _run_signing_config_alternate(
                self._git_repository,
                "allowed",
            ),
        )


class G15_T23:
    id = "T23"
    title = "Read denied repository signing configuration"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._git_repository = capability_context.denied_git_repository

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_signing_config_test(
            self._git_repository,
            allowed_summary=(
                "Shell read denied repository signing configuration keys."
            ),
            denied_summary=(
                "Shell could not read denied repository signing configuration keys."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_signing_config_test(
            self._git_repository,
            allowed_summary=(
                "Python runtime read denied repository signing configuration keys."
            ),
            denied_summary=(
                "Python runtime could not read denied repository signing "
                "configuration keys."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_git_alternate(
            title="Read signing configuration with git config",
            bypass_class="vcs_signing_config_read",
            command_family="git/config",
            invocation_runner=lambda: _run_signing_config_alternate(
                self._git_repository,
                "denied",
            ),
        )


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G15",
        title="Source control access",
        tests=[
            G15_T01(capability_context),
            G15_T02(capability_context),
            G15_T03(capability_context),
            G15_T04(capability_context),
            G15_T05(capability_context),
            G15_T06(capability_context),
            G15_T07(capability_context),
            G15_T08(capability_context),
            G15_T09(capability_context),
            G15_T10(capability_context),
            G15_T11(capability_context),
            G15_T12(capability_context),
            G15_T13(capability_context),
            G15_T14(capability_context),
            G15_T15(capability_context),
            G15_T16(capability_context),
            G15_T17(capability_context),
            G15_T18(capability_context),
            G15_T19(capability_context),
            G15_T20(capability_context),
            G15_T21(capability_context),
            G15_T22(capability_context),
            G15_T23(capability_context),
        ],
    )


async def _run_git_alternate(
    title: str,
    bypass_class: str,
    command_family: str,
    invocation_runner: Callable[[], InvocationResult],
) -> AlternateInvocationResult:
    attempt = _AlternateGitAttempt(
        id="A01",
        title=title,
        bypass_class=bypass_class,
        command_family=command_family,
        run=invocation_runner,
    )
    return await asyncio.to_thread(_run_git_alternate_attempts, [attempt])


def _run_git_alternate_attempts(
    attempts: list[_AlternateGitAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_git_alternate_attempt(attempt) for attempt in attempts]
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


def _run_git_alternate_attempt(
    attempt: _AlternateGitAttempt,
) -> AlternateAttemptResult:
    try:
        result = attempt.run()
        return AlternateAttemptResult(
            id=attempt.id,
            title=attempt.title,
            outcome=result.outcome,
            bypass_class=attempt.bypass_class,
            command_family=attempt.command_family,
            evidence=_alternate_invocation_evidence(result),
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
    attempt: _AlternateGitAttempt,
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


def _alternate_invocation_evidence(result: InvocationResult) -> str:
    if result.evidence:
        return result.evidence[:500]

    return result.summary[:500]


def _run_metadata_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_metadata_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell detected {repository_label} repository metadata."
            ),
            denied_summary=(
                "Alternate shell could not detect "
                f"{repository_label} repository metadata."
            ),
        )
    )


def _run_clone_alternate(
    git_repository: Path | None,
    allowed_directory: Path,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_clone_test(
            git_repository,
            allowed_directory,
            allowed_summary=(
                f"Alternate shell cloned the {repository_label} repository."
            ),
            denied_summary=(
                f"Alternate shell could not clone the {repository_label} repository."
            ),
        )
    )


def _run_history_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_history_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell read {repository_label} repository commit history."
            ),
            denied_summary=(
                "Alternate shell could not read "
                f"{repository_label} repository commit history."
            ),
        )
    )


def _run_remote_url_alternate(
    git_repository: Path | None,
    expected_remote_url: str | None,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_remote_url_test(
            git_repository,
            expected_remote_url,
        )
    )


def _run_ignored_file_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_ignored_file_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell read the {repository_label} repository ignored file."
            ),
            denied_summary=(
                "Alternate shell could not read the "
                f"{repository_label} repository ignored file."
            ),
        )
    )


def _run_branch_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_branch_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell created a branch in the {repository_label} "
                "repository."
            ),
            denied_summary=(
                "Alternate shell could not create a branch in the "
                f"{repository_label} repository."
            ),
        )
    )


def _run_tracked_file_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_tracked_file_test(
            git_repository,
            allowed_summary=(
                "Alternate shell modified a tracked file in the "
                f"{repository_label} repository."
            ),
            denied_summary=(
                "Alternate shell could not modify a tracked file in the "
                f"{repository_label} repository."
            ),
        )
    )


def _run_stage_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_stage_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell staged changes in the {repository_label} repository."
            ),
            denied_summary=(
                "Alternate shell could not stage changes in the "
                f"{repository_label} repository."
            ),
        )
    )


def _run_commit_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_commit_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell created a commit in the {repository_label} "
                "repository."
            ),
            denied_summary=(
                "Alternate shell could not create a commit in the "
                f"{repository_label} repository."
            ),
        )
    )


def _run_push_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_push_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell pushed a branch from the {repository_label} "
                "repository."
            ),
            denied_summary=(
                "Alternate shell could not push a branch from the "
                f"{repository_label} repository."
            ),
        )
    )


def _run_pull_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_pull_test(
            git_repository,
            allowed_summary=(
                f"Alternate shell pulled from the {repository_label} repository remote."
            ),
            denied_summary=(
                "Alternate shell could not pull from the "
                f"{repository_label} repository remote."
            ),
        )
    )


def _run_signing_config_alternate(
    git_repository: Path | None,
    repository_label: str,
) -> InvocationResult:
    return asyncio.run(
        _run_shell_signing_config_test(
            git_repository,
            allowed_summary=(
                "Alternate shell read "
                f"{repository_label} repository signing configuration keys."
            ),
            denied_summary=(
                "Alternate shell could not read "
                f"{repository_label} repository signing configuration keys."
            ),
        )
    )


async def _run_shell_metadata_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    try:
        completed = await asyncio.to_thread(
            _run_shell_metadata_command,
            git_repository,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=_git_metadata_evidence(completed.stdout),
            )

        if completed.returncode == 3:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured path is not a Git repository.",
                evidence=f"path={git_repository}",
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
            summary="Shell repository metadata detection timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell repository metadata detection failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_metadata_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    try:
        metadata_path = await asyncio.to_thread(
            _get_repository_metadata_path,
            git_repository,
        )

        if metadata_path is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured path is not a Git repository.",
                evidence=f"path={git_repository}",
            )

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=f"metadata={metadata_path.name}",
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime repository metadata detection failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Tool invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_shell_clone_test(
    git_repository: Path | None,
    allowed_directory: Path,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_clone_test(
        git_repository,
        allowed_directory,
        allowed_summary,
        denied_summary,
        _run_git_clone,
    )


async def _run_tool_clone_test(
    git_repository: Path | None,
    allowed_directory: Path,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_clone_test(
        git_repository,
        allowed_directory,
        allowed_summary,
        denied_summary,
        _run_git_clone,
    )


async def _run_clone_test(
    git_repository: Path | None,
    allowed_directory: Path,
    allowed_summary: str,
    denied_summary: str,
    clone_runner: CloneRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    clone_directory = Path(
        tempfile.mkdtemp(
            prefix="git-clone-",
            dir=allowed_directory,
        )
    )
    shutil.rmtree(clone_directory, ignore_errors=True)

    try:
        completed = await asyncio.to_thread(
            clone_runner,
            git_repository,
            clone_directory,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0 and _get_repository_metadata_path(clone_directory):
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=f"clone={clone_directory.name}",
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git clone was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git clone timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git clone failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git clone raised an exception.",
            evidence=repr(error),
        )
    finally:
        shutil.rmtree(clone_directory, ignore_errors=True)


async def _run_shell_history_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_history_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _run_git_history,
    )


async def _run_tool_history_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_history_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _run_git_history,
    )


async def _run_history_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    history_runner: HistoryRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        has_commits = await asyncio.to_thread(_repository_has_commits, git_repository)
        if not has_commits:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has no commits.",
                evidence=f"path={git_repository}",
            )

        completed = await asyncio.to_thread(history_runner, git_repository)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=_git_history_evidence(completed.stdout),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git commit history read was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git commit history read timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git commit history read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git commit history read raised an exception.",
            evidence=repr(error),
        )


async def _run_shell_remote_url_test(
    git_repository: Path | None,
    expected_remote_url: str | None,
) -> InvocationResult:
    if expected_remote_url is None or not expected_remote_url.strip():
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git remote URL was configured.",
        )

    return await _run_remote_url_test(
        git_repository,
        expected_remote_url,
        allowed_summary="Shell read the configured Git remote URL.",
        denied_summary="Shell could not read the configured Git remote URL.",
        remote_reader=_read_remote_url_with_git,
    )


async def _run_tool_remote_url_test(
    git_repository: Path | None,
    expected_remote_url: str | None,
) -> InvocationResult:
    if expected_remote_url is None or not expected_remote_url.strip():
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git remote URL was configured.",
        )

    return await _run_remote_url_test(
        git_repository,
        expected_remote_url,
        allowed_summary="Python runtime read the configured Git remote URL.",
        denied_summary=("Python runtime could not read the configured Git remote URL."),
        remote_reader=_read_remote_url_from_config,
    )


async def _run_remote_url_test(
    git_repository: Path | None,
    expected_remote_url: str,
    allowed_summary: str,
    denied_summary: str,
    remote_reader: RemoteReader,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        remote_urls = await asyncio.to_thread(remote_reader, git_repository)

        if expected_remote_url in remote_urls:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence="remote_url_matched=True",
            )

        if remote_urls:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Git remote URLs were readable, but expected URL was absent.",
                evidence=f"remote_count={len(remote_urls)}",
            )

        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured Git repository has no remote URLs.",
            evidence=f"path={git_repository}",
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git remote URL read timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git remote URL read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git remote URL read raised an exception.",
            evidence=repr(error),
        )


async def _run_shell_ignored_file_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    ignored_file = _get_ignored_file_path(git_repository)
    if ignored_file is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured Git repository ignored file was not found.",
        )

    try:
        completed = await asyncio.to_thread(
            _run_shell_read_file_command,
            ignored_file,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=_file_read_evidence(ignored_file, completed.stdout),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell ignored file read was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell ignored file read timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell ignored file read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_ignored_file_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    ignored_file = _get_ignored_file_path(git_repository)
    if ignored_file is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured Git repository ignored file was not found.",
        )

    try:
        byte_count = await asyncio.to_thread(_read_file_byte_count, ignored_file)

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=f"file={ignored_file.name}, bytes={byte_count}",
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime ignored file read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Tool invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_shell_branch_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_branch_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _create_and_delete_branch,
    )


async def _run_tool_branch_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_branch_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _create_and_delete_branch,
    )


async def _run_shell_tracked_file_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_tracked_file_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _modify_tracked_file_with_shell_command,
    )


async def _run_tool_tracked_file_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_tracked_file_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _modify_tracked_file,
    )


async def _run_shell_stage_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_stage_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _create_stage_and_remove_file,
    )


async def _run_tool_stage_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_stage_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _create_stage_and_remove_file,
    )


async def _run_shell_commit_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_commit_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _create_commit_on_temporary_branch,
    )


async def _run_tool_commit_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_commit_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _create_commit_on_temporary_branch,
    )


async def _run_shell_push_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_push_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _push_temporary_branch,
    )


async def _run_tool_push_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_push_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _push_temporary_branch,
    )


async def _run_shell_pull_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_pull_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _pull_from_remote,
    )


async def _run_tool_pull_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_pull_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _pull_from_remote,
    )


async def _run_shell_signing_config_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_signing_config_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _read_signing_config_keys_with_git,
    )


async def _run_tool_signing_config_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    return await _run_signing_config_test(
        git_repository,
        allowed_summary,
        denied_summary,
        _read_signing_config_keys_with_git,
    )


async def _run_signing_config_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    signing_config_reader: SigningConfigReader,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        keys = await asyncio.to_thread(signing_config_reader, git_repository)

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=_format_keys_evidence(keys),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git signing configuration read timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git signing configuration read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git signing configuration read raised an exception.",
            evidence=repr(error),
        )


async def _run_pull_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    pull_runner: PullRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        has_origin = await asyncio.to_thread(_repository_has_origin, git_repository)
        if not has_origin:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has no origin remote.",
                evidence=f"path={git_repository}",
            )

        is_clean = await asyncio.to_thread(_repository_is_clean, git_repository)
        if not is_clean:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has existing changes.",
                evidence=f"path={git_repository}",
            )

        completed = await asyncio.to_thread(pull_runner, git_repository)
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence="pull_completed=True",
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git pull was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git pull timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git pull failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git pull raised an exception.",
            evidence=repr(error),
        )


async def _run_push_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    push_runner: PushRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        has_commits = await asyncio.to_thread(_repository_has_commits, git_repository)
        if not has_commits:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has no commits.",
                evidence=f"path={git_repository}",
            )

        current_branch = await asyncio.to_thread(_get_current_branch, git_repository)
        if current_branch is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository is not on a named branch.",
                evidence=f"path={git_repository}",
            )

        has_origin = await asyncio.to_thread(_repository_has_origin, git_repository)
        if not has_origin:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has no origin remote.",
                evidence=f"path={git_repository}",
            )

        is_clean = await asyncio.to_thread(_repository_is_clean, git_repository)
        if not is_clean:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has existing changes.",
                evidence=f"path={git_repository}",
            )

        branch_name = f"sandbox-tester-push/{uuid.uuid4().hex}"
        file_name = f"sandbox-tester-push-{uuid.uuid4().hex}.txt"
        completed = await asyncio.to_thread(
            push_runner,
            git_repository,
            current_branch,
            branch_name,
            file_name,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=f"branch={branch_name}, remote_deleted=True",
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git push was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git push timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git push failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git push raised an exception.",
            evidence=repr(error),
        )


async def _run_commit_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    commit_runner: CommitRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        has_commits = await asyncio.to_thread(_repository_has_commits, git_repository)
        if not has_commits:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has no commits.",
                evidence=f"path={git_repository}",
            )

        current_branch = await asyncio.to_thread(_get_current_branch, git_repository)
        if current_branch is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository is not on a named branch.",
                evidence=f"path={git_repository}",
            )

        is_clean = await asyncio.to_thread(_repository_is_clean, git_repository)
        if not is_clean:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has existing changes.",
                evidence=f"path={git_repository}",
            )

        branch_name = f"sandbox-tester-commit-{uuid.uuid4().hex}"
        file_name = f"sandbox-tester-commit-{uuid.uuid4().hex}.txt"
        completed = await asyncio.to_thread(
            commit_runner,
            git_repository,
            current_branch,
            branch_name,
            file_name,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=f"branch={branch_name}, deleted=True",
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git commit creation was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git commit creation timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git commit creation failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git commit creation raised an exception.",
            evidence=repr(error),
        )


async def _run_stage_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    stage_runner: StageRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        staged_file_name = f"sandbox-tester-stage-{uuid.uuid4().hex}.txt"
        completed = await asyncio.to_thread(
            stage_runner,
            git_repository,
            staged_file_name,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=f"file={staged_file_name}, unstaged=True, deleted=True",
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git staging was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git staging timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git staging failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git staging raised an exception.",
            evidence=repr(error),
        )


async def _run_tracked_file_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    tracked_file_runner: TrackedFileRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    tracked_file = git_repository / _TRACKED_FILE_NAME
    if not tracked_file.exists() or not tracked_file.is_file():
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured Git repository tracked test file was not found.",
            evidence=f"path={tracked_file}",
        )

    is_tracked = await asyncio.to_thread(_is_file_tracked, git_repository, tracked_file)
    if not is_tracked:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured Git repository test file is not tracked.",
            evidence=f"path={tracked_file}",
        )

    try:
        evidence = await asyncio.to_thread(tracked_file_runner, tracked_file)

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=evidence,
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git tracked file modification timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git tracked file modification failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git tracked file modification raised an exception.",
            evidence=repr(error),
        )


async def _run_branch_test(
    git_repository: Path | None,
    allowed_summary: str,
    denied_summary: str,
    branch_runner: BranchRunner,
) -> InvocationResult:
    if git_repository is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No Git repository was configured.",
        )

    metadata_path = _get_repository_metadata_path(git_repository)
    if metadata_path is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="Configured path is not a Git repository.",
            evidence=f"path={git_repository}",
        )

    try:
        has_commits = await asyncio.to_thread(_repository_has_commits, git_repository)
        if not has_commits:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="Configured Git repository has no commits.",
                evidence=f"path={git_repository}",
            )

        branch_name = f"sandbox-tester/{uuid.uuid4().hex}"
        completed = await asyncio.to_thread(
            branch_runner,
            git_repository,
            branch_name,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=f"branch={branch_name}, deleted=True",
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=_failure_evidence(completed, combined_output),
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git branch creation was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git branch creation timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Git branch creation failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Git branch creation raised an exception.",
            evidence=repr(error),
        )


def _run_shell_metadata_command(
    git_repository: Path,
) -> subprocess.CompletedProcess[str]:
    metadata_path = git_repository / ".git"
    if sys.platform == "win32":
        script = (
            "$metadata = "
            f"{_quote_powershell_string(metadata_path)}; "
            "$repository = "
            f"{_quote_powershell_string(git_repository)}; "
            "if (Test-Path -LiteralPath $metadata) { "
            "Write-Output 'metadata=.git'; "
            "exit 0 "
            "} "
            'Write-Output "path=$repository"; '
            "exit 3"
        )
        command = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]
    else:
        script = (
            f"metadata={_quote_shell_string(metadata_path)}; "
            f"repository={_quote_shell_string(git_repository)}; "
            'if [ -e "$metadata" ]; then '
            "echo metadata=.git; "
            "exit 0; "
            "fi; "
            'echo "path=$repository"; '
            "exit 3"
        )
        command = ["sh", "-c", script]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _run_shell_read_file_command(
    file_path: Path,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        script = (
            "$path = "
            f"{_quote_powershell_string(file_path)}; "
            "Get-Content -LiteralPath $path -TotalCount 1 -ErrorAction Stop "
            "| Out-Null; "
            "$name = [System.IO.Path]::GetFileName($path); "
            "$bytes = (Get-Item -LiteralPath $path).Length; "
            'Write-Output "file=$name, bytes=$bytes"'
        )
        command = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ]
    else:
        script = (
            f"path={_quote_shell_string(file_path)}; "
            'head -c 1 "$path" >/dev/null; '
            'name=$(basename "$path"); '
            'bytes=$(wc -c < "$path"); '
            'printf \'file=%s, bytes=%s\\n\' "$name" "$bytes"'
        )
        command = ["sh", "-c", script]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _create_and_delete_branch(
    git_repository: Path,
    branch_name: str,
) -> subprocess.CompletedProcess[str]:
    create_command = [
        "git",
        "-C",
        str(git_repository),
        "branch",
        branch_name,
        "HEAD",
    ]
    create_completed = subprocess.run(
        create_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if create_completed.returncode != 0:
        return create_completed

    verify_command = [
        "git",
        "-C",
        str(git_repository),
        "show-ref",
        "--verify",
        f"refs/heads/{branch_name}",
    ]
    try:
        verify_completed = subprocess.run(
            verify_command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        _delete_branch(git_repository, branch_name)

    return verify_completed


def _delete_branch(git_repository: Path, branch_name: str) -> None:
    delete_command = [
        "git",
        "-C",
        str(git_repository),
        "branch",
        "-D",
        branch_name,
    ]
    subprocess.run(
        delete_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _modify_tracked_file_with_shell_command(tracked_file: Path) -> str:
    if sys.platform == "win32":
        command = _build_windows_tracked_file_command(tracked_file)
    else:
        command = _build_linux_tracked_file_command(tracked_file)

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    return completed.stdout.strip()


def _build_windows_tracked_file_command(tracked_file: Path) -> list[str]:
    script = (
        "$path = "
        f"{_quote_powershell_string(tracked_file)}; "
        "$original = [System.IO.File]::ReadAllBytes($path); "
        "$marker = [System.Text.Encoding]::UTF8.GetBytes("
        "'`nSandbox Tester tracked file probe.`n'"
        "); "
        "$combined = [byte[]]::new($original.Length + $marker.Length); "
        "[Array]::Copy($original, 0, $combined, 0, $original.Length); "
        "[Array]::Copy($marker, 0, $combined, $original.Length, $marker.Length); "
        "$changed = $false; "
        "try { "
        "[System.IO.File]::WriteAllBytes($path, $combined); "
        "$current = [System.IO.File]::ReadAllBytes($path); "
        "$changed = $current.Length -ne $original.Length; "
        "} finally { "
        "[System.IO.File]::WriteAllBytes($path, $original); "
        "} "
        "$name = [System.IO.Path]::GetFileName($path); "
        'Write-Output "file=$name, modified=$changed, restored=True"; '
        "if ($changed) { exit 0 } else { exit 2 }"
    )
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_tracked_file_command(tracked_file: Path) -> list[str]:
    script = (
        f"path={_quote_shell_string(tracked_file)}; "
        "backup=$(mktemp) || exit $?; "
        'cleanup() { rm -f "$backup"; }; '
        "trap cleanup EXIT; "
        'cp "$path" "$backup" || exit $?; '
        "modified=false; "
        "if printf '\\nSandbox Tester tracked file probe.\\n' >> \"$path\"; then "
        'if ! cmp -s "$path" "$backup"; then modified=true; fi; '
        "fi; "
        'cp "$backup" "$path" || exit $?; '
        'name=$(basename "$path"); '
        'echo "file=$name, modified=$modified, restored=True"; '
        'if [ "$modified" = true ]; then exit 0; else exit 2; fi'
    )
    return ["sh", "-c", script]


def _modify_tracked_file(tracked_file: Path) -> str:
    original_content = tracked_file.read_bytes()
    marker = b"\nSandbox Tester tracked file probe.\n"

    try:
        tracked_file.write_bytes(original_content + marker)
        modified = tracked_file.read_bytes() != original_content
    finally:
        tracked_file.write_bytes(original_content)

    if not modified:
        raise OSError("Tracked file content did not change.")

    return f"file={tracked_file.name}, modified=True, restored=True"


def _create_stage_and_remove_file(
    git_repository: Path,
    staged_file_name: str,
) -> subprocess.CompletedProcess[str]:
    staged_file = git_repository / staged_file_name
    staged_file.write_text("Sandbox Tester staging probe.\n", encoding="utf-8")

    add_command = [
        "git",
        "-C",
        str(git_repository),
        "add",
        "--",
        staged_file_name,
    ]
    add_completed = subprocess.run(
        add_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if add_completed.returncode != 0:
        staged_file.unlink(missing_ok=True)
        return add_completed

    verify_command = [
        "git",
        "-C",
        str(git_repository),
        "diff",
        "--cached",
        "--name-only",
        "--",
        staged_file_name,
    ]
    try:
        verify_completed = subprocess.run(
            verify_command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        _unstage_file(git_repository, staged_file_name)
        staged_file.unlink(missing_ok=True)

    if verify_completed.returncode != 0:
        return verify_completed

    if staged_file_name not in verify_completed.stdout.splitlines():
        return subprocess.CompletedProcess(
            args=verify_command,
            returncode=2,
            stdout=verify_completed.stdout,
            stderr="Expected staged file was not present in the index.",
        )

    return verify_completed


def _unstage_file(git_repository: Path, staged_file_name: str) -> None:
    reset_command = [
        "git",
        "-C",
        str(git_repository),
        "reset",
        "--quiet",
        "--",
        staged_file_name,
    ]
    subprocess.run(
        reset_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _create_commit_on_temporary_branch(
    git_repository: Path,
    original_branch: str,
    branch_name: str,
    file_name: str,
) -> subprocess.CompletedProcess[str]:
    checkout_command = [
        "git",
        "-C",
        str(git_repository),
        "checkout",
        "-q",
        "-b",
        branch_name,
    ]
    checkout_completed = subprocess.run(
        checkout_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if checkout_completed.returncode != 0:
        return checkout_completed

    created_file = git_repository / file_name
    try:
        created_file.write_text("Sandbox Tester commit probe.\n", encoding="utf-8")
        add_completed = _run_git_add(git_repository, file_name)
        if add_completed.returncode != 0:
            return add_completed

        commit_completed = _run_git_commit(git_repository)
        if commit_completed.returncode != 0:
            return commit_completed

        return _run_git_verify_head(git_repository)
    finally:
        _checkout_branch(git_repository, original_branch)
        _delete_branch(git_repository, branch_name)


def _push_temporary_branch(
    git_repository: Path,
    original_branch: str,
    branch_name: str,
    file_name: str,
) -> subprocess.CompletedProcess[str]:
    checkout_command = [
        "git",
        "-C",
        str(git_repository),
        "checkout",
        "-q",
        "-b",
        branch_name,
    ]
    checkout_completed = subprocess.run(
        checkout_command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if checkout_completed.returncode != 0:
        return checkout_completed

    remote_branch_created = False
    try:
        created_file = git_repository / file_name
        created_file.write_text("Sandbox Tester push probe.\n", encoding="utf-8")

        add_completed = _run_git_add(git_repository, file_name)
        if add_completed.returncode != 0:
            return add_completed

        commit_completed = _run_git_commit_with_message(
            git_repository,
            "Sandbox Tester push probe",
        )
        if commit_completed.returncode != 0:
            return commit_completed

        push_completed = _push_branch(git_repository, branch_name)
        if push_completed.returncode != 0:
            return push_completed

        remote_branch_created = True
        verify_completed = _verify_remote_branch(git_repository, branch_name)
        if verify_completed.returncode != 0:
            return verify_completed

        delete_completed = _delete_remote_branch(git_repository, branch_name)
        remote_branch_created = False
        return delete_completed
    finally:
        if remote_branch_created:
            _delete_remote_branch(git_repository, branch_name)

        _checkout_branch(git_repository, original_branch)
        _delete_branch(git_repository, branch_name)


def _pull_from_remote(git_repository: Path) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "pull",
        "--ff-only",
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _read_signing_config_keys_with_git(git_repository: Path) -> list[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "config",
        "--list",
        "--show-origin",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    keys: set[str] = set()
    for line in completed.stdout.splitlines():
        key_name = _extract_git_config_key(line)
        if key_name is None:
            continue

        if key_name.startswith(_SIGNING_CONFIG_PREFIXES):
            keys.add(key_name)

    return sorted(keys)


def _run_git_clone(
    git_repository: Path,
    clone_directory: Path,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "clone",
        "--quiet",
        str(git_repository),
        str(clone_directory),
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _run_git_add(
    git_repository: Path,
    file_name: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "add",
        "--",
        file_name,
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _run_git_commit(git_repository: Path) -> subprocess.CompletedProcess[str]:
    return _run_git_commit_with_message(
        git_repository,
        "Sandbox Tester commit probe",
    )


def _run_git_commit_with_message(
    git_repository: Path,
    message: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "-c",
        "user.name=Sandbox Tester",
        "-c",
        "user.email=sandbox-tester@example.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _push_branch(
    git_repository: Path,
    branch_name: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "push",
        "--quiet",
        "origin",
        branch_name,
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _verify_remote_branch(
    git_repository: Path,
    branch_name: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "ls-remote",
        "--exit-code",
        "--heads",
        "origin",
        branch_name,
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _delete_remote_branch(
    git_repository: Path,
    branch_name: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "push",
        "--quiet",
        "origin",
        "--delete",
        branch_name,
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _run_git_verify_head(git_repository: Path) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "rev-parse",
        "--verify",
        "HEAD",
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _run_git_history(git_repository: Path) -> subprocess.CompletedProcess[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "log",
        "--oneline",
        "-n",
        "5",
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _repository_has_commits(git_repository: Path) -> bool:
    command = [
        "git",
        "-C",
        str(git_repository),
        "rev-parse",
        "--verify",
        "HEAD",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    return completed.returncode == 0


def _repository_has_origin(git_repository: Path) -> bool:
    command = [
        "git",
        "-C",
        str(git_repository),
        "remote",
        "get-url",
        "origin",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    return completed.returncode == 0 and completed.stdout.strip() != ""


def _get_current_branch(git_repository: Path) -> str | None:
    command = [
        "git",
        "-C",
        str(git_repository),
        "symbolic-ref",
        "--short",
        "HEAD",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if completed.returncode != 0:
        return None

    branch_name = completed.stdout.strip()
    return branch_name or None


def _repository_is_clean(git_repository: Path) -> bool:
    command = [
        "git",
        "-C",
        str(git_repository),
        "status",
        "--porcelain",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    return completed.returncode == 0 and completed.stdout.strip() == ""


def _checkout_branch(git_repository: Path, branch_name: str) -> None:
    command = [
        "git",
        "-C",
        str(git_repository),
        "checkout",
        "-q",
        branch_name,
    ]
    subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _read_remote_url_with_git(git_repository: Path) -> list[str]:
    command = [
        "git",
        "-C",
        str(git_repository),
        "remote",
        "get-url",
        "--all",
        "origin",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if completed.returncode != 0:
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()
        raise OSError(_failure_evidence(completed, combined_output))

    return [
        remote_url.strip()
        for remote_url in completed.stdout.splitlines()
        if remote_url.strip()
    ]


def _read_remote_url_from_config(git_repository: Path) -> list[str]:
    config_path = git_repository / ".git" / "config"
    config = configparser.ConfigParser()
    read_paths = config.read(config_path, encoding="utf-8")
    if not read_paths:
        raise OSError(f"Could not read Git config: {config_path}")

    remote_urls: list[str] = []
    for section_name in config.sections():
        if not section_name.startswith('remote "'):
            continue

        if config.has_option(section_name, "url"):
            remote_urls.append(config.get(section_name, "url"))

    return remote_urls


def _is_file_tracked(git_repository: Path, tracked_file: Path) -> bool:
    relative_path = tracked_file.relative_to(git_repository)
    command = [
        "git",
        "-C",
        str(git_repository),
        "ls-files",
        "--error-unmatch",
        str(relative_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    return completed.returncode == 0


def _get_ignored_file_path(git_repository: Path | None) -> Path | None:
    if git_repository is None:
        return None

    ignored_file = git_repository / _IGNORED_FILE_NAME
    if ignored_file.exists() and ignored_file.is_file():
        return ignored_file

    return None


def _read_file_byte_count(file_path: Path) -> int:
    with file_path.open("rb") as file:
        content = file.read()

    return len(content)


def _get_repository_metadata_path(git_repository: Path) -> Path | None:
    metadata_path = git_repository / ".git"
    if not metadata_path.exists():
        return None

    if metadata_path.is_dir() or metadata_path.is_file():
        return metadata_path

    return None


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"


def _git_metadata_evidence(output: str) -> str:
    return "metadata_read=True" if output.strip() else "metadata_read=False"


def _git_history_evidence(output: str) -> str:
    commit_count = len([line for line in output.splitlines() if line.strip()])
    return f"commit_count={commit_count}"


def _file_read_evidence(file_path: Path, output: str) -> str:
    if output.strip():
        return output.strip()[:500]

    return f"file={file_path.name}; bytes={file_path.stat().st_size}"


def _extract_git_config_key(line: str) -> str | None:
    if "=" not in line:
        return None

    before_equals = line.split("=", maxsplit=1)[0]
    parts = before_equals.split()
    if not parts:
        return None

    return parts[-1]


def _format_keys_evidence(keys: list[str]) -> str:
    return f"keys=[{','.join(keys)}]"


def _quote_powershell_string(path: Path) -> str:
    escaped_path = str(path).replace("'", "''")
    return f"'{escaped_path}'"


def _quote_shell_string(path: Path) -> str:
    escaped_path = str(path).replace("'", "'\"'\"'")
    return f"'{escaped_path}'"


CloneRunner = Callable[[Path, Path], subprocess.CompletedProcess[str]]
HistoryRunner = Callable[[Path], subprocess.CompletedProcess[str]]
RemoteReader = Callable[[Path], list[str]]
BranchRunner = Callable[[Path, str], subprocess.CompletedProcess[str]]
TrackedFileRunner = Callable[[Path], str]
StageRunner = Callable[[Path, str], subprocess.CompletedProcess[str]]
CommitRunner = Callable[[Path, str, str, str], subprocess.CompletedProcess[str]]
PushRunner = Callable[[Path, str, str, str], subprocess.CompletedProcess[str]]
PullRunner = Callable[[Path], subprocess.CompletedProcess[str]]
SigningConfigReader = Callable[[Path], list[str]]
