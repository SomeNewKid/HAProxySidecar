"""A reporter for printing results."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .models import AlternateInvocationResult, InvocationResult


class TestReporter(Protocol):
    def group_started(self, group_id: str, group_title: str) -> None: ...

    def group_skipped(self, group_id: str, group_title: str) -> None: ...

    def capability_started(
        self, group_id: str, capability_id: str, capability_title: str
    ) -> None: ...

    def shell_completed(self, result: InvocationResult) -> None: ...

    def tool_completed(self, result: InvocationResult) -> None: ...

    def alternates_completed(self, result: AlternateInvocationResult) -> None: ...


class ConsoleReporter:
    def group_started(self, group_id: str, group_title: str) -> None:
        print()
        print(f"{group_id} {group_title}")
        print("-" * 20)

    def group_skipped(self, group_id: str, group_title: str) -> None:
        print()
        print(f"`{group_id} `(skipped) {group_title}")
        print("-" * 20)

    def capability_started(
        self, group_id: str, capability_id: str, capability_title: str
    ) -> None:
        print(f"  {group_id} {capability_id} {capability_title}")

    def shell_completed(self, result: InvocationResult) -> None:
        print(f"    shell: {result.outcome}")

    def tool_completed(self, result: InvocationResult) -> None:
        print(f"    tool:  {result.outcome}")

    def alternates_completed(self, result: AlternateInvocationResult) -> None:
        print(f"    alt:   {result.outcome}")


class QuietReporter:
    def group_started(self, group_id: str, group_title: str) -> None:
        # the suite is too long running to not print anything.
        print(f"{group_id} {group_title}")

    def group_skipped(self, group_id: str, group_title: str) -> None:
        print(f"{group_id} (skipped) {group_title} ")

    def capability_started(
        self, group_id: str, capability_id: str, capability_title: str
    ) -> None:
        pass

    def shell_completed(self, result: InvocationResult) -> None:
        pass

    def tool_completed(self, result: InvocationResult) -> None:
        pass

    def alternates_completed(self, result: AlternateInvocationResult) -> None:
        pass


class StatusFileReporter:
    """Write real-time test status events to a newline-delimited JSON file."""

    def __init__(self, status_path: Path) -> None:
        self._status_path = status_path
        self._status_path.parent.mkdir(parents=True, exist_ok=True)

    def group_started(self, group_id: str, group_title: str) -> None:
        self._write_event(
            "group_started",
            group_id=group_id,
            group_title=group_title,
            message=f"{group_id} {group_title}",
        )

    def group_skipped(self, group_id: str, group_title: str) -> None:
        self._write_event(
            "group_skipped",
            group_id=group_id,
            group_title=group_title,
            message=f"{group_id} (skipped) {group_title}",
        )

    def capability_started(
        self, group_id: str, capability_id: str, capability_title: str
    ) -> None:
        self._write_event(
            "capability_started",
            group_id=group_id,
            capability_id=capability_id,
            capability_title=capability_title,
            message=f"{group_id} {capability_id} {capability_title}",
        )

    def shell_completed(self, result: InvocationResult) -> None:
        self._write_event(
            "shell_completed",
            outcome=result.outcome,
            summary=result.summary,
        )

    def tool_completed(self, result: InvocationResult) -> None:
        self._write_event(
            "tool_completed",
            outcome=result.outcome,
            summary=result.summary,
        )

    def alternates_completed(self, result: AlternateInvocationResult) -> None:
        self._write_event(
            "alternates_completed",
            outcome=result.outcome,
            summary=result.summary,
        )

    def _write_event(self, event_type: str, **fields: object) -> None:
        event = {
            "event_type": event_type,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            **fields,
        }
        event_json = json.dumps(event, default=str)
        with self._status_path.open("a", encoding="utf-8") as status_file:
            status_file.write(f"{event_json}\n")


class CompositeReporter:
    """Send test status events to multiple reporters."""

    def __init__(self, reporters: list[TestReporter]) -> None:
        self._reporters = reporters

    def group_started(self, group_id: str, group_title: str) -> None:
        for reporter in self._reporters:
            reporter.group_started(group_id, group_title)

    def group_skipped(self, group_id: str, group_title: str) -> None:
        for reporter in self._reporters:
            reporter.group_skipped(group_id, group_title)

    def capability_started(
        self, group_id: str, capability_id: str, capability_title: str
    ) -> None:
        for reporter in self._reporters:
            reporter.capability_started(group_id, capability_id, capability_title)

    def shell_completed(self, result: InvocationResult) -> None:
        for reporter in self._reporters:
            reporter.shell_completed(result)

    def tool_completed(self, result: InvocationResult) -> None:
        for reporter in self._reporters:
            reporter.tool_completed(result)

    def alternates_completed(self, result: AlternateInvocationResult) -> None:
        for reporter in self._reporters:
            reporter.alternates_completed(result)
