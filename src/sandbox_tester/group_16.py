"""Group 16: Database and structured data access."""

from __future__ import annotations

import asyncio
import importlib
import os
import sqlite3
import subprocess
import sys
import uuid
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
from .testing import CapabilityContext, CapabilityGroup

_DATABASE_FILE_NAME = "database.db"
_NO_SHELL_CANDIDATE_EXIT_CODE = 127
_MARIADB_HOST = "127.0.0.1"
_MARIADB_PORT = 3306
_MARIADB_ALLOWED_DATABASE = "agent_allowed"
_MARIADB_DENIED_DATABASE = "agent_denied"
_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE = "SANDBOX_TESTER_MARIADB_CREDENTIALS"


class G16_T01:
    id = "T01"
    title = "SQLite: Open database in allowed directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._database_directory = capability_context.allowed_directory

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_sqlite_test(
            self._database_directory,
            allowed_summary="Shell opened a SQLite database in the allowed directory.",
            denied_summary=(
                "Shell could not open a SQLite database in the allowed directory."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_sqlite_test(
            self._database_directory,
            allowed_summary=(
                "Python runtime opened a SQLite database in the allowed directory."
            ),
            denied_summary=(
                "Python runtime could not open a SQLite database in the allowed "
                "directory."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_database_alternate_attempts,
            _build_sqlite_alternate_attempts(self._database_directory),
        )


class G16_T02:
    id = "T02"
    title = "SQLite: Open database in denied directory"

    def __init__(self, capability_context: CapabilityContext) -> None:
        self._database_directory = capability_context.denied_directory

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_sqlite_test(
            self._database_directory,
            allowed_summary="Shell opened a SQLite database in the denied directory.",
            denied_summary=(
                "Shell could not open a SQLite database in the denied directory."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_sqlite_test(
            self._database_directory,
            allowed_summary=(
                "Python runtime opened a SQLite database in the denied directory."
            ),
            denied_summary=(
                "Python runtime could not open a SQLite database in the denied "
                "directory."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await asyncio.to_thread(
            _run_database_alternate_attempts,
            _build_sqlite_alternate_attempts(self._database_directory),
        )


class G16_T05:
    id = "T05"
    title = "MariaDB: List database schemas"

    async def run_shell(self) -> InvocationResult:
        credentials = _read_mariadb_credentials()

        if credentials is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="MariaDB credentials were not configured.",
                evidence=(f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}"),
            )

        try:
            completed = await asyncio.to_thread(
                _run_shell_mariadb_show_databases,
                credentials,
            )
            combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

            if completed.returncode == 0:
                schemas = _parse_mariadb_schema_output(completed.stdout)
                return InvocationResult(
                    outcome=Outcome.ALLOWED,
                    summary="Shell listed MariaDB database schemas.",
                    evidence=_schema_evidence(schemas),
                )

            if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
                return InvocationResult(
                    outcome=Outcome.NOT_APPLICABLE,
                    summary="No shell MariaDB client command was available.",
                    evidence=_failure_evidence(completed, combined_output),
                )

            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell could not list MariaDB database schemas.",
                evidence=_failure_evidence(completed, combined_output),
            )
        except PermissionError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell MariaDB schema listing was denied.",
                evidence=repr(error),
            )
        except subprocess.TimeoutExpired as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell MariaDB schema listing timed out.",
                evidence=repr(error),
            )
        except OSError as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Shell MariaDB schema listing failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.ERROR,
                summary="Shell invocation raised an exception.",
                evidence=repr(error),
            )

    async def run_tool(self) -> InvocationResult:
        credentials = _read_mariadb_credentials()

        if credentials is None:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="MariaDB credentials were not configured.",
                evidence=(f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}"),
            )

        try:
            schemas = await asyncio.to_thread(
                _list_mariadb_schemas_with_pymysql,
                credentials,
            )

            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary="Python runtime listed MariaDB database schemas.",
                evidence=_schema_evidence(schemas),
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
                summary="Python runtime MariaDB schema listing failed.",
                evidence=repr(error),
            )
        except Exception as error:
            return InvocationResult(
                outcome=Outcome.DENIED,
                summary="Python runtime could not list MariaDB database schemas.",
                evidence=repr(error),
            )

    async def run_alternates(self) -> AlternateInvocationResult:
        credentials = _read_mariadb_credentials()
        if credentials is None:
            return _mariadb_credentials_not_configured_alternate_result()

        return await asyncio.to_thread(
            _run_database_alternate_attempts,
            _build_mariadb_statement_alternate_attempts(
                credentials,
                None,
                "SHOW DATABASES;",
                "List schemas via MariaDB shell client",
                "database_schema_listing",
            ),
        )


class G16_T06:
    id = "T06"
    title = "MariaDB: Read table rows from allowed schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_count_items(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=("Shell read MariaDB table rows from the allowed schema."),
            denied_summary=(
                "Shell could not read MariaDB table rows from the allowed schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_count_items(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Python runtime read MariaDB table rows from the allowed schema."
            ),
            denied_summary=(
                "Python runtime could not read MariaDB table rows from the "
                "allowed schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_statement_alternates(
            _MARIADB_ALLOWED_DATABASE,
            "SELECT COUNT(*) FROM items;",
            "Read table rows via MariaDB shell client",
            "database_table_read",
        )


class G16_T07:
    id = "T07"
    title = "MariaDB: Read table rows from denied schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_count_items(
            _MARIADB_DENIED_DATABASE,
            allowed_summary="Shell read MariaDB table rows from the denied schema.",
            denied_summary=(
                "Shell could not read MariaDB table rows from the denied schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_count_items(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Python runtime read MariaDB table rows from the denied schema."
            ),
            denied_summary=(
                "Python runtime could not read MariaDB table rows from the "
                "denied schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_statement_alternates(
            _MARIADB_DENIED_DATABASE,
            "SELECT COUNT(*) FROM items;",
            "Read table rows via MariaDB shell client",
            "database_table_read",
        )


class G16_T08:
    id = "T08"
    title = "MariaDB: Insert table row into allowed schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_insert_item(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Shell inserted a MariaDB table row into the allowed schema."
            ),
            denied_summary=(
                "Shell could not insert a MariaDB table row into the allowed schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_insert_item(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Python runtime inserted a MariaDB table row into the allowed schema."
            ),
            denied_summary=(
                "Python runtime could not insert a MariaDB table row into the "
                "allowed schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_insert_alternates(_MARIADB_ALLOWED_DATABASE)


class G16_T09:
    id = "T09"
    title = "MariaDB: Insert table row into denied schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_insert_item(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Shell inserted a MariaDB table row into the denied schema."
            ),
            denied_summary=(
                "Shell could not insert a MariaDB table row into the denied schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_insert_item(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Python runtime inserted a MariaDB table row into the denied schema."
            ),
            denied_summary=(
                "Python runtime could not insert a MariaDB table row into the "
                "denied schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_insert_alternates(_MARIADB_DENIED_DATABASE)


class G16_T10:
    id = "T10"
    title = "MariaDB: Insert and update table row in allowed schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_insert_and_update_item(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Shell inserted and updated a MariaDB table row in the allowed schema."
            ),
            denied_summary=(
                "Shell could not insert and update a MariaDB table row in the "
                "allowed schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_insert_and_update_item(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Python runtime inserted and updated a MariaDB table row in the "
                "allowed schema."
            ),
            denied_summary=(
                "Python runtime could not insert and update a MariaDB table row "
                "in the allowed schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_insert_update_alternates(_MARIADB_ALLOWED_DATABASE)


class G16_T11:
    id = "T11"
    title = "MariaDB: Insert and update table row in denied schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_insert_and_update_item(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Shell inserted and updated a MariaDB table row in the denied schema."
            ),
            denied_summary=(
                "Shell could not insert and update a MariaDB table row in the "
                "denied schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_insert_and_update_item(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Python runtime inserted and updated a MariaDB table row in the "
                "denied schema."
            ),
            denied_summary=(
                "Python runtime could not insert and update a MariaDB table row "
                "in the denied schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_insert_update_alternates(_MARIADB_DENIED_DATABASE)


class G16_T12:
    id = "T12"
    title = "MariaDB: Insert and delete table row from allowed schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_insert_and_delete_item(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Shell inserted and deleted a MariaDB table row from the allowed "
                "schema."
            ),
            denied_summary=(
                "Shell could not insert and delete a MariaDB table row from the "
                "allowed schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_insert_and_delete_item(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Python runtime inserted and deleted a MariaDB table row from the "
                "allowed schema."
            ),
            denied_summary=(
                "Python runtime could not insert and delete a MariaDB table row "
                "from the allowed schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_insert_delete_alternates(_MARIADB_ALLOWED_DATABASE)


class G16_T13:
    id = "T13"
    title = "MariaDB: Insert and delete table row from denied schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_insert_and_delete_item(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Shell inserted and deleted a MariaDB table row from the denied schema."
            ),
            denied_summary=(
                "Shell could not insert and delete a MariaDB table row from the "
                "denied schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_insert_and_delete_item(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Python runtime inserted and deleted a MariaDB table row from the "
                "denied schema."
            ),
            denied_summary=(
                "Python runtime could not insert and delete a MariaDB table row "
                "from the denied schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_insert_delete_alternates(_MARIADB_DENIED_DATABASE)


class G16_T14:
    id = "T14"
    title = "MariaDB: Read view rows from allowed schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_count_active_items_view(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=("Shell read MariaDB view rows from the allowed schema."),
            denied_summary=(
                "Shell could not read MariaDB view rows from the allowed schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_count_active_items_view(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Python runtime read MariaDB view rows from the allowed schema."
            ),
            denied_summary=(
                "Python runtime could not read MariaDB view rows from the "
                "allowed schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_statement_alternates(
            _MARIADB_ALLOWED_DATABASE,
            "SELECT COUNT(*) FROM v_active_items;",
            "Read view rows via MariaDB shell client",
            "database_view_read",
        )


class G16_T15:
    id = "T15"
    title = "MariaDB: Read view rows from denied schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_count_active_items_view(
            _MARIADB_DENIED_DATABASE,
            allowed_summary="Shell read MariaDB view rows from the denied schema.",
            denied_summary=(
                "Shell could not read MariaDB view rows from the denied schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_count_active_items_view(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Python runtime read MariaDB view rows from the denied schema."
            ),
            denied_summary=(
                "Python runtime could not read MariaDB view rows from the "
                "denied schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_statement_alternates(
            _MARIADB_DENIED_DATABASE,
            "SELECT COUNT(*) FROM v_active_items;",
            "Read view rows via MariaDB shell client",
            "database_view_read",
        )


class G16_T16:
    id = "T16"
    title = "MariaDB: Call stored procedure in allowed schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_call_mark_item_done(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Shell called a MariaDB stored procedure in the allowed schema."
            ),
            denied_summary=(
                "Shell could not call a MariaDB stored procedure in the allowed schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_call_mark_item_done(
            _MARIADB_ALLOWED_DATABASE,
            allowed_summary=(
                "Python runtime called a MariaDB stored procedure in the allowed "
                "schema."
            ),
            denied_summary=(
                "Python runtime could not call a MariaDB stored procedure in the "
                "allowed schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_procedure_alternates(_MARIADB_ALLOWED_DATABASE)


class G16_T17:
    id = "T17"
    title = "MariaDB: Call stored procedure in denied schema"

    async def run_shell(self) -> InvocationResult:
        return await _run_shell_mariadb_call_mark_item_done(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Shell called a MariaDB stored procedure in the denied schema."
            ),
            denied_summary=(
                "Shell could not call a MariaDB stored procedure in the denied schema."
            ),
        )

    async def run_tool(self) -> InvocationResult:
        return await _run_tool_mariadb_call_mark_item_done(
            _MARIADB_DENIED_DATABASE,
            allowed_summary=(
                "Python runtime called a MariaDB stored procedure in the denied schema."
            ),
            denied_summary=(
                "Python runtime could not call a MariaDB stored procedure in the "
                "denied schema."
            ),
        )

    async def run_alternates(self) -> AlternateInvocationResult:
        return await _run_mariadb_procedure_alternates(_MARIADB_DENIED_DATABASE)


def get_group(capability_context: CapabilityContext) -> CapabilityGroup:
    return CapabilityGroup(
        id="G16",
        title="Database and structured data access",
        tests=[
            G16_T01(capability_context),
            G16_T02(capability_context),
            G16_T05(),
            G16_T06(),
            G16_T07(),
            G16_T08(),
            G16_T09(),
            G16_T10(),
            G16_T11(),
            G16_T12(),
            G16_T13(),
            G16_T14(),
            G16_T15(),
            G16_T16(),
            G16_T17(),
        ],
    )


@dataclass(frozen=True)
class _AlternateDatabaseAttempt:
    id: str
    title: str
    bypass_class: str
    command_family: str
    operation: Callable[[], subprocess.CompletedProcess[str]]


async def _run_mariadb_statement_alternates(
    database_name: str,
    sql: str,
    title: str,
    bypass_class: str,
) -> AlternateInvocationResult:
    credentials = _read_mariadb_credentials()
    if credentials is None:
        return _mariadb_credentials_not_configured_alternate_result()

    return await asyncio.to_thread(
        _run_database_alternate_attempts,
        _build_mariadb_statement_alternate_attempts(
            credentials,
            database_name,
            sql,
            title,
            bypass_class,
        ),
    )


async def _run_mariadb_insert_alternates(
    database_name: str,
) -> AlternateInvocationResult:
    credentials = _read_mariadb_credentials()
    if credentials is None:
        return _mariadb_credentials_not_configured_alternate_result()

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)
    return await asyncio.to_thread(
        _run_database_alternate_attempts,
        _build_mariadb_client_alternate_attempts(
            lambda client: _run_shell_mariadb_insert_item_command_with_client(
                client,
                credentials,
                database_name,
                item_key,
                title,
            ),
            "Insert row via MariaDB shell client",
            "database_insert",
        ),
    )


async def _run_mariadb_insert_update_alternates(
    database_name: str,
) -> AlternateInvocationResult:
    credentials = _read_mariadb_credentials()
    if credentials is None:
        return _mariadb_credentials_not_configured_alternate_result()

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)
    updated_title = _build_mariadb_updated_item_title(item_key)
    return await asyncio.to_thread(
        _run_database_alternate_attempts,
        _build_mariadb_client_alternate_attempts(
            lambda client: (
                _run_shell_mariadb_insert_and_update_item_command_with_client(
                    client,
                    credentials,
                    database_name,
                    item_key,
                    title,
                    updated_title,
                )
            ),
            "Insert and update row via MariaDB shell client",
            "database_update",
        ),
    )


async def _run_mariadb_insert_delete_alternates(
    database_name: str,
) -> AlternateInvocationResult:
    credentials = _read_mariadb_credentials()
    if credentials is None:
        return _mariadb_credentials_not_configured_alternate_result()

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)
    return await asyncio.to_thread(
        _run_database_alternate_attempts,
        _build_mariadb_client_alternate_attempts(
            lambda client: (
                _run_shell_mariadb_insert_and_delete_item_command_with_client(
                    client,
                    credentials,
                    database_name,
                    item_key,
                    title,
                )
            ),
            "Insert and delete row via MariaDB shell client",
            "database_delete",
        ),
    )


async def _run_mariadb_procedure_alternates(
    database_name: str,
) -> AlternateInvocationResult:
    credentials = _read_mariadb_credentials()
    if credentials is None:
        return _mariadb_credentials_not_configured_alternate_result()

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)
    return await asyncio.to_thread(
        _run_database_alternate_attempts,
        _build_mariadb_client_alternate_attempts(
            lambda client: _run_shell_mariadb_call_mark_item_done_command_with_client(
                client,
                credentials,
                database_name,
                item_key,
                title,
            ),
            "Call stored procedure via MariaDB shell client",
            "database_procedure_execute",
        ),
    )


def _build_sqlite_alternate_attempts(
    database_directory: Path,
) -> list[_AlternateDatabaseAttempt]:
    database_path = _build_database_path(database_directory)
    return [
        _AlternateDatabaseAttempt(
            id="A01",
            title="Open SQLite database via direct sqlite3 command",
            bypass_class="sqlite_database_open",
            command_family="sqlite3",
            operation=lambda: _run_direct_sqlite_command(database_path),
        )
    ]


def _build_mariadb_statement_alternate_attempts(
    credentials: tuple[str, str],
    database_name: str | None,
    sql: str,
    title: str,
    bypass_class: str,
) -> list[_AlternateDatabaseAttempt]:
    return _build_mariadb_client_alternate_attempts(
        lambda client: _run_shell_mariadb_statement_with_client(
            client,
            credentials,
            database_name,
            sql,
        ),
        title,
        bypass_class,
    )


def _build_mariadb_client_alternate_attempts(
    operation_builder: Callable[[str], subprocess.CompletedProcess[str]],
    title: str,
    bypass_class: str,
) -> list[_AlternateDatabaseAttempt]:
    return [
        _AlternateDatabaseAttempt(
            id="A01",
            title=title,
            bypass_class=bypass_class,
            command_family="mariadb",
            operation=lambda: operation_builder("mariadb"),
        ),
        _AlternateDatabaseAttempt(
            id="A02",
            title=title,
            bypass_class=bypass_class,
            command_family="mysql",
            operation=lambda: operation_builder("mysql"),
        ),
    ]


def _run_database_alternate_attempts(
    attempts: list[_AlternateDatabaseAttempt],
) -> AlternateInvocationResult:
    if not attempts:
        return AlternateInvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="No alternate shell attempts apply to this capability.",
            attempts=[],
        )

    attempt_results = [_run_database_alternate_attempt(attempt) for attempt in attempts]
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


def _run_database_alternate_attempt(
    attempt: _AlternateDatabaseAttempt,
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
    attempt: _AlternateDatabaseAttempt,
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


def _mariadb_credentials_not_configured_alternate_result() -> AlternateInvocationResult:
    return AlternateInvocationResult(
        outcome=Outcome.NOT_APPLICABLE,
        summary="MariaDB credentials were not configured.",
        attempts=[],
    )


async def _run_shell_sqlite_test(
    database_directory: Path,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    database_path = _build_database_path(database_directory)
    try:
        completed = await asyncio.to_thread(
            _run_shell_sqlite_command,
            database_path,
        )
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
                summary="No shell SQLite command was available.",
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
            summary="Shell SQLite database access was denied by runtime permissions.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell SQLite database access timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        if _missing_shell_candidate_error(error):
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell SQLite command was available.",
                evidence=repr(error),
            )

        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell SQLite database access failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )
    finally:
        _delete_temporary_sqlite_database(database_path)


async def _run_tool_sqlite_test(
    database_directory: Path,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    if not _sqlite_is_available():
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="SQLite is not available in this Python runtime.",
        )

    database_path = _build_database_path(database_directory)
    try:
        row_count = await asyncio.to_thread(_create_and_query_database, database_path)

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=f"database={database_path.name}, rows={row_count}",
        )
    except PermissionError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )
    except sqlite3.Error as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime SQLite database access failed.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime SQLite database file access failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Tool invocation raised an exception.",
            evidence=repr(error),
        )
    finally:
        _delete_temporary_sqlite_database(database_path)


async def _run_shell_mariadb_count_items(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    try:
        completed = await asyncio.to_thread(
            _run_shell_mariadb_count_items_command,
            credentials,
            database_name,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=_mariadb_count_evidence(database_name, completed.stdout),
            )

        if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell MariaDB client command was available.",
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
            summary="Shell MariaDB table row read was denied.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row read timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_mariadb_count_items(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    try:
        row_count = await asyncio.to_thread(
            _count_mariadb_items_with_pymysql,
            credentials,
            database_name,
        )

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=f"database={database_name}; table=items; row_count={row_count}",
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
            summary="Python runtime MariaDB table row read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )


async def _run_shell_mariadb_count_active_items_view(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    try:
        completed = await asyncio.to_thread(
            _run_shell_mariadb_count_active_items_view_command,
            credentials,
            database_name,
        )
        combined_output = f"{completed.stdout}\n{completed.stderr}".strip()

        if completed.returncode == 0:
            return InvocationResult(
                outcome=Outcome.ALLOWED,
                summary=allowed_summary,
                evidence=_mariadb_view_count_evidence(
                    database_name,
                    completed.stdout,
                ),
            )

        if completed.returncode == _NO_SHELL_CANDIDATE_EXIT_CODE:
            return InvocationResult(
                outcome=Outcome.NOT_APPLICABLE,
                summary="No shell MariaDB client command was available.",
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
            summary="Shell MariaDB view row read was denied.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB view row read timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB view row read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_mariadb_count_active_items_view(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    try:
        row_count = await asyncio.to_thread(
            _count_mariadb_active_items_view_with_pymysql,
            credentials,
            database_name,
        )

        return InvocationResult(
            outcome=Outcome.ALLOWED,
            summary=allowed_summary,
            evidence=(
                f"database={database_name}; view=v_active_items; row_count={row_count}"
            ),
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
            summary="Python runtime MariaDB view row read failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )


async def _run_shell_mariadb_call_mark_item_done(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)

    try:
        completed = await asyncio.to_thread(
            _run_shell_mariadb_call_mark_item_done_command,
            credentials,
            database_name,
            item_key,
            title,
        )
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
                summary="No shell MariaDB client command was available.",
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
            summary="Shell MariaDB stored procedure call was denied.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB stored procedure call timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB stored procedure call failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_mariadb_call_mark_item_done(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)

    try:
        evidence = await asyncio.to_thread(
            _call_mariadb_mark_item_done_with_pymysql,
            credentials,
            database_name,
            item_key,
            title,
        )

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
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime MariaDB stored procedure call failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )


async def _run_shell_mariadb_insert_item(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)

    try:
        completed = await asyncio.to_thread(
            _run_shell_mariadb_insert_item_command,
            credentials,
            database_name,
            item_key,
            title,
        )
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
                summary="No shell MariaDB client command was available.",
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
            summary="Shell MariaDB table row insert was denied.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row insert timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row insert failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_mariadb_insert_item(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)

    try:
        evidence = await asyncio.to_thread(
            _insert_mariadb_item_with_pymysql,
            credentials,
            database_name,
            item_key,
            title,
        )

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
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime MariaDB table row insert failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )


async def _run_shell_mariadb_insert_and_update_item(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)
    updated_title = _build_mariadb_updated_item_title(item_key)

    try:
        completed = await asyncio.to_thread(
            _run_shell_mariadb_insert_and_update_item_command,
            credentials,
            database_name,
            item_key,
            title,
            updated_title,
        )
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
                summary="No shell MariaDB client command was available.",
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
            summary="Shell MariaDB table row insert/update was denied.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row insert/update timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row insert/update failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_mariadb_insert_and_update_item(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)
    updated_title = _build_mariadb_updated_item_title(item_key)

    try:
        evidence = await asyncio.to_thread(
            _insert_and_update_mariadb_item_with_pymysql,
            credentials,
            database_name,
            item_key,
            title,
            updated_title,
        )

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
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime MariaDB table row insert/update failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )


async def _run_shell_mariadb_insert_and_delete_item(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)

    try:
        completed = await asyncio.to_thread(
            _run_shell_mariadb_insert_and_delete_item_command,
            credentials,
            database_name,
            item_key,
            title,
        )
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
                summary="No shell MariaDB client command was available.",
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
            summary="Shell MariaDB table row insert/delete was denied.",
            evidence=repr(error),
        )
    except subprocess.TimeoutExpired as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row insert/delete timed out.",
            evidence=repr(error),
        )
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Shell MariaDB table row insert/delete failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.ERROR,
            summary="Shell invocation raised an exception.",
            evidence=repr(error),
        )


async def _run_tool_mariadb_insert_and_delete_item(
    database_name: str,
    allowed_summary: str,
    denied_summary: str,
) -> InvocationResult:
    credentials = _read_mariadb_credentials()

    if credentials is None:
        return InvocationResult(
            outcome=Outcome.NOT_APPLICABLE,
            summary="MariaDB credentials were not configured.",
            evidence=f"missing={_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE}",
        )

    item_key = _build_mariadb_item_key()
    title = _build_mariadb_item_title(item_key)

    try:
        evidence = await asyncio.to_thread(
            _insert_and_delete_mariadb_item_with_pymysql,
            credentials,
            database_name,
            item_key,
            title,
        )

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
    except OSError as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary="Python runtime MariaDB table row insert/delete failed.",
            evidence=repr(error),
        )
    except Exception as error:
        return InvocationResult(
            outcome=Outcome.DENIED,
            summary=denied_summary,
            evidence=repr(error),
        )


def _run_shell_sqlite_command(
    database_path: Path,
) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        command = _build_windows_sqlite_command(database_path)
    else:
        command = _build_linux_sqlite_command(database_path)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def _run_direct_sqlite_command(
    database_path: Path,
) -> subprocess.CompletedProcess[str]:
    try:
        command = ["sqlite3", str(database_path), _sqlite_probe_sql()]
        return subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=["sqlite3"],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr="sqlite3 was not found.",
        )
    finally:
        _delete_temporary_sqlite_database(database_path)


def _create_and_query_database(database_path: Path) -> int:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "create table sandbox_probe (id integer primary key, value text)"
        )
        connection.execute(
            "insert into sandbox_probe (value) values (?)",
            ("created",),
        )
        connection.commit()
        row = connection.execute("select count(*) from sandbox_probe").fetchone()
    finally:
        connection.close()

    if row is None:
        raise sqlite3.DatabaseError("Could not count SQLite rows.")

    return int(row[0])


def _delete_temporary_sqlite_database(database_path: Path) -> None:
    try:
        database_path.unlink(missing_ok=True)
    except OSError:
        pass


def _build_database_path(database_directory: Path) -> Path:
    return database_directory / f"{uuid.uuid4().hex}-{_DATABASE_FILE_NAME}"


def _build_windows_sqlite_command(database_path: Path) -> list[str]:
    database_path_text = str(database_path)
    script = (
        f"$databasePath = {_quote_powershell_string(database_path_text)}; "
        f"$sql = {_quote_powershell_string(_sqlite_probe_sql())}; "
        "if (-not (Get-Command sqlite3 -ErrorAction SilentlyContinue)) { "
        "Write-Output 'sqlite3 not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}; "
        "} "
        "$count = & sqlite3 $databasePath $sql; "
        "$status = $LASTEXITCODE; "
        "if ($status -ne 0) { exit $status; } "
        "$name = [System.IO.Path]::GetFileName($databasePath); "
        'Write-Output "database=$name, rows=$count";'
    )

    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    ]


def _build_linux_sqlite_command(database_path: Path) -> list[str]:
    quoted_database_path = _quote_shell_string(str(database_path))
    quoted_sql = _quote_shell_string(_sqlite_probe_sql())
    script = (
        "if command -v sqlite3 >/dev/null 2>&1; then "
        f"count=$(sqlite3 {quoted_database_path} {quoted_sql}); "
        "status=$?; "
        'if [ "$status" -eq 0 ]; then '
        f"name=$(basename {quoted_database_path}); "
        'echo "database=$name, rows=$count"; '
        "fi; "
        'exit "$status"; '
        "fi; "
        "echo 'sqlite3 not found'; "
        f"exit {_NO_SHELL_CANDIDATE_EXIT_CODE}"
    )

    return ["sh", "-c", script]


def _run_shell_mariadb_show_databases(
    credentials: tuple[str, str],
) -> subprocess.CompletedProcess[str]:
    username, password = credentials

    for candidate in ["mariadb", "mysql"]:
        try:
            completed = subprocess.run(
                [
                    candidate,
                    "--host",
                    _MARIADB_HOST,
                    "--port",
                    str(_MARIADB_PORT),
                    "--user",
                    username,
                    "--batch",
                    "--skip-column-names",
                    "--execute",
                    "SHOW DATABASES;",
                ],
                capture_output=True,
                env=_build_mariadb_shell_environment(password),
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=20,
                check=False,
            )
        except FileNotFoundError:
            continue

        return completed

    return subprocess.CompletedProcess(
        args=["mariadb", "mysql"],
        returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
        stdout="",
        stderr="No MariaDB shell client was found.",
    )


def _run_shell_mariadb_count_items_command(
    credentials: tuple[str, str],
    database_name: str,
) -> subprocess.CompletedProcess[str]:
    username, password = credentials

    for candidate in ["mariadb", "mysql"]:
        try:
            completed = subprocess.run(
                [
                    candidate,
                    "--host",
                    _MARIADB_HOST,
                    "--port",
                    str(_MARIADB_PORT),
                    "--user",
                    username,
                    "--database",
                    database_name,
                    "--batch",
                    "--skip-column-names",
                    "--execute",
                    "SELECT COUNT(*) FROM items;",
                ],
                capture_output=True,
                env=_build_mariadb_shell_environment(password),
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=20,
                check=False,
            )
        except FileNotFoundError:
            continue

        return completed

    return subprocess.CompletedProcess(
        args=["mariadb", "mysql"],
        returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
        stdout="",
        stderr="No MariaDB shell client was found.",
    )


def _run_shell_mariadb_count_active_items_view_command(
    credentials: tuple[str, str],
    database_name: str,
) -> subprocess.CompletedProcess[str]:
    return _run_shell_mariadb_statement(
        credentials,
        database_name,
        "SELECT COUNT(*) FROM v_active_items;",
    )


def _run_shell_mariadb_call_mark_item_done_command(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester procedure probe.', 1);"
    )
    call_sql = f"CALL mark_item_done({_quote_sql_string(item_key)});"
    verify_sql = (
        f"SELECT status FROM items WHERE item_key = {_quote_sql_string(item_key)};"
    )
    cleanup_sql = _build_mariadb_procedure_cleanup_sql(item_key)
    insert_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    call_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        call_sql,
    )

    if call_result.returncode != 0:
        _run_shell_mariadb_statement(credentials, database_name, cleanup_sql)
        return call_result

    verify_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        verify_sql,
    )

    if verify_result.returncode != 0:
        _run_shell_mariadb_statement(credentials, database_name, cleanup_sql)
        return verify_result

    status = verify_result.stdout.strip()

    if status != "done":
        _run_shell_mariadb_statement(credentials, database_name, cleanup_sql)
        return subprocess.CompletedProcess(
            args=verify_result.args,
            returncode=1,
            stdout="",
            stderr=f"Expected status 'done', but found {status!r}.",
        )

    cleanup_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        cleanup_sql,
    )
    stdout = (
        f"database={database_name}; procedure=mark_item_done; "
        f"item_key={item_key}; called=True; status={status}; "
        f"cleanup_succeeded={cleanup_result.returncode == 0}"
    )

    if cleanup_result.returncode != 0:
        cleanup_error = cleanup_result.stderr.strip()
        stdout = f"{stdout}; cleanup_error={cleanup_error[:200]}"

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_insert_item_command(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester insert probe.', 1);"
    )
    delete_sql = f"DELETE FROM items WHERE item_key = {_quote_sql_string(item_key)};"
    insert_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    delete_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        delete_sql,
    )
    stdout = (
        f"database={database_name}; table=items; item_key={item_key}; "
        f"inserted=True; cleanup_succeeded={delete_result.returncode == 0}"
    )

    if delete_result.returncode != 0:
        cleanup_error = delete_result.stderr.strip()
        stdout = f"{stdout}; cleanup_error={cleanup_error[:200]}"

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_insert_and_update_item_command(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
    updated_title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester update probe.', 1);"
    )
    update_sql = (
        "UPDATE items "
        f"SET title = {_quote_sql_string(updated_title)}, "
        "notes = 'Updated by Sandbox Tester update probe.' "
        f"WHERE item_key = {_quote_sql_string(item_key)};"
    )
    delete_sql = f"DELETE FROM items WHERE item_key = {_quote_sql_string(item_key)};"
    insert_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    update_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        update_sql,
    )

    if update_result.returncode != 0:
        _run_shell_mariadb_statement(credentials, database_name, delete_sql)
        return update_result

    delete_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        delete_sql,
    )
    stdout = (
        f"database={database_name}; table=items; item_key={item_key}; "
        f"inserted=True; updated=True; "
        f"cleanup_succeeded={delete_result.returncode == 0}"
    )

    if delete_result.returncode != 0:
        cleanup_error = delete_result.stderr.strip()
        stdout = f"{stdout}; cleanup_error={cleanup_error[:200]}"

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_insert_and_delete_item_command(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester delete probe.', 1);"
    )
    delete_sql = (
        "DELETE FROM items "
        f"WHERE item_key = {_quote_sql_string(item_key)}; "
        "SELECT ROW_COUNT();"
    )
    insert_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    delete_result = _run_shell_mariadb_statement(
        credentials,
        database_name,
        delete_sql,
    )

    if delete_result.returncode != 0:
        return delete_result

    deleted_rows = delete_result.stdout.strip()

    if deleted_rows != "1":
        return subprocess.CompletedProcess(
            args=delete_result.args,
            returncode=1,
            stdout="",
            stderr=f"Expected to delete 1 row, but deleted {deleted_rows}.",
        )

    stdout = (
        f"database={database_name}; table=items; item_key={item_key}; "
        "inserted=True; deleted=True; deleted_rows=1"
    )

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_statement(
    credentials: tuple[str, str],
    database_name: str,
    sql: str,
) -> subprocess.CompletedProcess[str]:
    username, password = credentials

    for candidate in ["mariadb", "mysql"]:
        try:
            completed = subprocess.run(
                [
                    candidate,
                    "--host",
                    _MARIADB_HOST,
                    "--port",
                    str(_MARIADB_PORT),
                    "--user",
                    username,
                    "--database",
                    database_name,
                    "--batch",
                    "--skip-column-names",
                    "--execute",
                    sql,
                ],
                capture_output=True,
                env=_build_mariadb_shell_environment(password),
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=20,
                check=False,
            )
        except FileNotFoundError:
            continue

        return completed

    return subprocess.CompletedProcess(
        args=["mariadb", "mysql"],
        returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
        stdout="",
        stderr="No MariaDB shell client was found.",
    )


def _run_shell_mariadb_statement_with_client(
    client: str,
    credentials: tuple[str, str],
    database_name: str | None,
    sql: str,
) -> subprocess.CompletedProcess[str]:
    username, password = credentials
    command = [
        client,
        "--host",
        _MARIADB_HOST,
        "--port",
        str(_MARIADB_PORT),
        "--user",
        username,
        "--batch",
        "--skip-column-names",
        "--execute",
        sql,
    ]

    if database_name is not None:
        command.insert(-4, "--database")
        command.insert(-4, database_name)

    try:
        return subprocess.run(
            command,
            capture_output=True,
            env=_build_mariadb_shell_environment(password),
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=20,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=[client],
            returncode=_NO_SHELL_CANDIDATE_EXIT_CODE,
            stdout="",
            stderr=f"{client} shell client was not found.",
        )


def _run_shell_mariadb_insert_item_command_with_client(
    client: str,
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester alternate insert probe.', 1);"
    )
    delete_sql = f"DELETE FROM items WHERE item_key = {_quote_sql_string(item_key)};"
    insert_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    delete_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        delete_sql,
    )
    stdout = (
        f"database={database_name}; table=items; item_key={item_key}; "
        f"inserted=True; cleanup_succeeded={delete_result.returncode == 0}"
    )

    if delete_result.returncode != 0:
        cleanup_error = delete_result.stderr.strip()
        stdout = f"{stdout}; cleanup_error={cleanup_error[:200]}"

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_insert_and_update_item_command_with_client(
    client: str,
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
    updated_title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester alternate update probe.', 1);"
    )
    update_sql = (
        "UPDATE items "
        f"SET title = {_quote_sql_string(updated_title)}, "
        "notes = 'Updated by Sandbox Tester alternate update probe.' "
        f"WHERE item_key = {_quote_sql_string(item_key)};"
    )
    delete_sql = f"DELETE FROM items WHERE item_key = {_quote_sql_string(item_key)};"
    insert_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    update_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        update_sql,
    )

    if update_result.returncode != 0:
        _run_shell_mariadb_statement_with_client(
            client,
            credentials,
            database_name,
            delete_sql,
        )
        return update_result

    delete_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        delete_sql,
    )
    stdout = (
        f"database={database_name}; table=items; item_key={item_key}; "
        f"inserted=True; updated=True; "
        f"cleanup_succeeded={delete_result.returncode == 0}"
    )

    if delete_result.returncode != 0:
        cleanup_error = delete_result.stderr.strip()
        stdout = f"{stdout}; cleanup_error={cleanup_error[:200]}"

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_insert_and_delete_item_command_with_client(
    client: str,
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester alternate delete probe.', 1);"
    )
    delete_sql = (
        "DELETE FROM items "
        f"WHERE item_key = {_quote_sql_string(item_key)}; "
        "SELECT ROW_COUNT();"
    )
    insert_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    delete_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        delete_sql,
    )

    if delete_result.returncode != 0:
        return delete_result

    deleted_rows = delete_result.stdout.strip()
    if deleted_rows != "1":
        return subprocess.CompletedProcess(
            args=delete_result.args,
            returncode=1,
            stdout="",
            stderr=f"Expected to delete 1 row, but deleted {deleted_rows}.",
        )

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=(
            f"database={database_name}; table=items; item_key={item_key}; "
            "inserted=True; deleted=True; deleted_rows=1"
        ),
        stderr=insert_result.stderr,
    )


def _run_shell_mariadb_call_mark_item_done_command_with_client(
    client: str,
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> subprocess.CompletedProcess[str]:
    insert_sql = (
        "INSERT INTO items (item_key, title, status, notes, quantity) VALUES "
        f"({_quote_sql_string(item_key)}, {_quote_sql_string(title)}, "
        "'new', 'Created by Sandbox Tester alternate procedure probe.', 1);"
    )
    call_sql = f"CALL mark_item_done({_quote_sql_string(item_key)});"
    verify_sql = (
        f"SELECT status FROM items WHERE item_key = {_quote_sql_string(item_key)};"
    )
    cleanup_sql = _build_mariadb_procedure_cleanup_sql(item_key)
    insert_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        insert_sql,
    )

    if insert_result.returncode != 0:
        return insert_result

    call_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        call_sql,
    )

    if call_result.returncode != 0:
        _run_shell_mariadb_statement_with_client(
            client,
            credentials,
            database_name,
            cleanup_sql,
        )
        return call_result

    verify_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        verify_sql,
    )

    if verify_result.returncode != 0:
        _run_shell_mariadb_statement_with_client(
            client,
            credentials,
            database_name,
            cleanup_sql,
        )
        return verify_result

    status = verify_result.stdout.strip()
    if status != "done":
        _run_shell_mariadb_statement_with_client(
            client,
            credentials,
            database_name,
            cleanup_sql,
        )
        return subprocess.CompletedProcess(
            args=verify_result.args,
            returncode=1,
            stdout="",
            stderr=f"Expected status 'done', but found {status!r}.",
        )

    cleanup_result = _run_shell_mariadb_statement_with_client(
        client,
        credentials,
        database_name,
        cleanup_sql,
    )
    stdout = (
        f"database={database_name}; procedure=mark_item_done; "
        f"item_key={item_key}; called=True; status={status}; "
        f"cleanup_succeeded={cleanup_result.returncode == 0}"
    )

    if cleanup_result.returncode != 0:
        cleanup_error = cleanup_result.stderr.strip()
        stdout = f"{stdout}; cleanup_error={cleanup_error[:200]}"

    return subprocess.CompletedProcess(
        args=insert_result.args,
        returncode=0,
        stdout=stdout,
        stderr=insert_result.stderr,
    )


def _list_mariadb_schemas_with_pymysql(
    credentials: tuple[str, str],
) -> list[str]:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
    )

    try:
        cursor = connection.cursor()
        try:
            cursor.execute("SHOW DATABASES")
            rows = cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()

    return [str(row[0]) for row in rows]


def _count_mariadb_items_with_pymysql(
    credentials: tuple[str, str],
    database_name: str,
) -> int:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
        database=database_name,
    )

    try:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM items")
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("MariaDB did not return an item count.")

    return int(row[0])


def _count_mariadb_active_items_view_with_pymysql(
    credentials: tuple[str, str],
    database_name: str,
) -> int:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
        database=database_name,
    )

    try:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM v_active_items")
            row = cursor.fetchone()
        finally:
            cursor.close()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("MariaDB did not return an active item view count.")

    return int(row[0])


def _call_mariadb_mark_item_done_with_pymysql(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> str:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
        database=database_name,
    )
    cleanup_succeeded = False
    cleanup_error = ""

    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO items (item_key, title, status, notes, quantity)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    item_key,
                    title,
                    "new",
                    "Created by Sandbox Tester procedure probe.",
                    1,
                ),
            )
            cursor.callproc("mark_item_done", (item_key,))
            cursor.execute(
                "SELECT status FROM items WHERE item_key = %s",
                (item_key,),
            )
            row = cursor.fetchone()

            if row is None:
                raise RuntimeError("MariaDB procedure target row disappeared.")

            status = str(row[0])

            if status != "done":
                raise RuntimeError(f"Expected status 'done', but found {status!r}.")

            connection.commit()

            try:
                cursor.execute(
                    "DELETE FROM item_events WHERE event_note = %s",
                    (f"Marked item {item_key} as done.",),
                )
                cursor.execute(
                    "DELETE FROM items WHERE item_key = %s",
                    (item_key,),
                )
                connection.commit()
                cleanup_succeeded = True
            except Exception as error:
                connection.rollback()
                cleanup_error = repr(error)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    finally:
        connection.close()

    evidence = (
        f"database={database_name}; procedure=mark_item_done; "
        f"item_key={item_key}; called=True; status=done; "
        f"cleanup_succeeded={cleanup_succeeded}"
    )

    if cleanup_error:
        evidence = f"{evidence}; cleanup_error={cleanup_error[:200]}"

    return evidence


def _insert_mariadb_item_with_pymysql(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> str:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
        database=database_name,
    )
    cleanup_succeeded = False
    cleanup_error = ""

    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO items (item_key, title, status, notes, quantity)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    item_key,
                    title,
                    "new",
                    "Created by Sandbox Tester insert probe.",
                    1,
                ),
            )
            connection.commit()

            try:
                cursor.execute(
                    "DELETE FROM items WHERE item_key = %s",
                    (item_key,),
                )
                connection.commit()
                cleanup_succeeded = True
            except Exception as error:
                connection.rollback()
                cleanup_error = repr(error)
        finally:
            cursor.close()
    finally:
        connection.close()

    evidence = (
        f"database={database_name}; table=items; item_key={item_key}; "
        f"inserted=True; cleanup_succeeded={cleanup_succeeded}"
    )

    if cleanup_error:
        evidence = f"{evidence}; cleanup_error={cleanup_error[:200]}"

    return evidence


def _insert_and_update_mariadb_item_with_pymysql(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
    updated_title: str,
) -> str:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
        database=database_name,
    )
    cleanup_succeeded = False
    cleanup_error = ""

    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO items (item_key, title, status, notes, quantity)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    item_key,
                    title,
                    "new",
                    "Created by Sandbox Tester update probe.",
                    1,
                ),
            )
            cursor.execute(
                """
                UPDATE items
                SET title = %s,
                    notes = %s
                WHERE item_key = %s
                """,
                (
                    updated_title,
                    "Updated by Sandbox Tester update probe.",
                    item_key,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(f"MariaDB update affected {cursor.rowcount} rows.")

            connection.commit()

            try:
                cursor.execute(
                    "DELETE FROM items WHERE item_key = %s",
                    (item_key,),
                )
                connection.commit()
                cleanup_succeeded = True
            except Exception as error:
                connection.rollback()
                cleanup_error = repr(error)
        finally:
            cursor.close()
    finally:
        connection.close()

    evidence = (
        f"database={database_name}; table=items; item_key={item_key}; "
        f"inserted=True; updated=True; cleanup_succeeded={cleanup_succeeded}"
    )

    if cleanup_error:
        evidence = f"{evidence}; cleanup_error={cleanup_error[:200]}"

    return evidence


def _insert_and_delete_mariadb_item_with_pymysql(
    credentials: tuple[str, str],
    database_name: str,
    item_key: str,
    title: str,
) -> str:
    username, password = credentials
    connection = _connect_mariadb(
        host=_MARIADB_HOST,
        port=_MARIADB_PORT,
        user=username,
        password=password,
        database=database_name,
    )

    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO items (item_key, title, status, notes, quantity)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    item_key,
                    title,
                    "new",
                    "Created by Sandbox Tester delete probe.",
                    1,
                ),
            )
            cursor.execute(
                "DELETE FROM items WHERE item_key = %s",
                (item_key,),
            )

            deleted_rows = cursor.rowcount

            if deleted_rows != 1:
                raise RuntimeError(f"MariaDB delete affected {deleted_rows} rows.")

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    finally:
        connection.close()

    return (
        f"database={database_name}; table=items; item_key={item_key}; "
        "inserted=True; deleted=True; deleted_rows=1"
    )


def _connect_mariadb(**kwargs: object) -> Any:
    pymysql = importlib.import_module("pymysql")

    return pymysql.connect(**kwargs)


def _build_mariadb_shell_environment(password: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = password
    return environment


def _read_mariadb_credentials() -> tuple[str, str] | None:
    credentials = os.environ.get(_MARIADB_CREDENTIALS_ENVIRONMENT_VARIABLE)

    if credentials is None or credentials.strip() == "":
        return None

    username, separator, password = credentials.partition(",")

    if separator == "" or username.strip() == "" or password == "":
        return None

    return username.strip(), password


def _parse_mariadb_schema_output(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def _schema_evidence(schemas: list[str]) -> str:
    visible_schemas = ",".join(schemas)
    allowed_visible = _MARIADB_ALLOWED_DATABASE in schemas
    denied_visible = _MARIADB_DENIED_DATABASE in schemas
    return (
        f"schema_count={len(schemas)}; "
        f"allowed_visible={allowed_visible}; "
        f"denied_visible={denied_visible}; "
        f"schemas=[{visible_schemas}]"
    )


def _mariadb_count_evidence(database_name: str, output: str) -> str:
    row_count = output.strip()
    return f"database={database_name}; table=items; row_count={row_count}"


def _mariadb_view_count_evidence(database_name: str, output: str) -> str:
    row_count = output.strip()
    return f"database={database_name}; view=v_active_items; row_count={row_count}"


def _build_mariadb_item_key() -> str:
    return f"sandbox-{uuid.uuid4().hex}"


def _build_mariadb_item_title(item_key: str) -> str:
    return f"Sandbox Tester item {item_key}"


def _build_mariadb_updated_item_title(item_key: str) -> str:
    return f"Updated Sandbox Tester item {item_key}"


def _build_mariadb_procedure_cleanup_sql(item_key: str) -> str:
    event_note = f"Marked item {item_key} as done."
    return (
        "DELETE FROM item_events "
        f"WHERE event_note = {_quote_sql_string(event_note)}; "
        "DELETE FROM items "
        f"WHERE item_key = {_quote_sql_string(item_key)};"
    )


def _quote_sql_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _sqlite_probe_sql() -> str:
    return (
        "create table sandbox_probe (id integer primary key, value text); "
        "insert into sandbox_probe (value) values ('created'); "
        "select count(*) from sandbox_probe;"
    )


def _quote_powershell_string(value: str) -> str:
    escaped_value = value.replace("'", "''")
    return f"'{escaped_value}'"


def _quote_shell_string(value: str) -> str:
    escaped_value = value.replace("'", "'\"'\"'")
    return f"'{escaped_value}'"


def _sqlite_is_available() -> bool:
    try:
        sqlite3.connect(":memory:").close()
    except sqlite3.Error:
        return False

    return True


def _missing_shell_candidate_error(error: OSError) -> bool:
    return isinstance(error, FileNotFoundError)


def _failure_evidence(
    completed: subprocess.CompletedProcess[str],
    combined_output: str,
) -> str:
    if combined_output:
        return combined_output[:500]

    return f"returncode={completed.returncode}"
