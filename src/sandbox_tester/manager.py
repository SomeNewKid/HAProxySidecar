"""Acts as the facade to the sandbox tester."""

from collections.abc import Callable

from .group_01 import get_group as get_group_01
from .group_02 import get_group as get_group_02
from .group_03 import get_group as get_group_03
from .group_04 import get_group as get_group_04
from .group_05 import get_group as get_group_05
from .group_06 import get_group as get_group_06
from .group_07 import get_group as get_group_07
from .group_08 import get_group as get_group_08
from .group_09 import get_group as get_group_09
from .group_10 import get_group as get_group_10
from .group_11 import get_group as get_group_11
from .group_12 import get_group as get_group_12
from .group_13 import get_group as get_group_13
from .group_14 import get_group as get_group_14
from .group_15 import get_group as get_group_15
from .group_16 import get_group as get_group_16
from .group_17 import get_group as get_group_17
from .group_18 import get_group as get_group_18
from .group_19 import get_group as get_group_19
from .group_20 import get_group as get_group_20
from .group_21 import get_group as get_group_21
from .group_22 import get_group as get_group_22
from .group_30 import get_group as get_group_30
from .reporter import TestReporter
from .testing import (
    CapabilityContext,
    CapabilityGroup,
    CapabilityGroupResult,
    run_group,
)

_ENABLED_GROUPS: list[str] = [
    "G01",
    "G02",
    "G03",
    "G04",
    "G05",
    "G06",
    "G07",
    "G08",
    "G09",
    "G10",
    "G11",
    "G12",
    "G13",
    "G14",
    "G15",
    "G16",
    "G17",
    "G18",
    "G19",
    "G20",
    "G21",
    "G22",
    "G30",
]

GROUP_FACTORIES: list[Callable[[CapabilityContext], CapabilityGroup]] = [
    get_group_01,
    get_group_02,
    get_group_03,
    get_group_04,
    get_group_05,
    get_group_06,
    get_group_07,
    get_group_08,
    get_group_09,
    get_group_10,
    get_group_11,
    get_group_12,
    get_group_13,
    get_group_14,
    get_group_15,
    get_group_16,
    get_group_17,
    get_group_18,
    get_group_19,
    get_group_20,
    get_group_21,
    get_group_22,
    get_group_30,
]


async def run_all_groups(
    capability_context: CapabilityContext,
    reporter: TestReporter,
) -> list[CapabilityGroupResult]:
    all_group_results: list[CapabilityGroupResult] = []

    for group_factory in GROUP_FACTORIES:
        group = group_factory(capability_context)
        if group.id not in _ENABLED_GROUPS:
            reporter.group_skipped(group.id, group.title)
            continue
        group_result = await run_group(group, reporter)
        all_group_results.append(group_result)

    return all_group_results
