# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Parse the `--csv` output of BabelStream 5.0.

With `--csv`, BabelStream prints two tables to stdout: the phase table (Init,
Read) and the kernel table (Copy, Mul, Add, Triad, Dot). Some models also
print free-form lines in between; the CUDA model reports the device, the
driver and the memory mode that way, and those are picked up as well.

Validation failures go to stderr and do not change the exit status, so they
have to be looked for explicitly.
"""

import dataclasses as _dataclasses
import re as _re

# ------------------------------------------------------------------------------
# Table layout
# ------------------------------------------------------------------------------

_PHASE_HEADER = (
    "phase",
    "n_elements",
    "sizeof",
    "max_mbytes_per_sec",
    "runtime",
)
_KERNEL_HEADER = (
    "function",
    "num_times",
    "n_elements",
    "sizeof",
    "max_mbytes_per_sec",
    "min_runtime",
    "max_runtime",
    "avg_runtime",
)

# Number of arrays each kernel moves per iteration, as BabelStream counts it.
KERNEL_ARRAYS = {"Copy": 2, "Mul": 2, "Add": 3, "Triad": 3, "Dot": 2}

_DEVICE_PATTERNS = {
    "name": _re.compile(r"^Using CUDA device (?P<value>.+)$"),
    "driver": _re.compile(r"^Driver: (?P<value>.+)$"),
    "memory_mode": _re.compile(r"^Memory: (?P<value>\w+)$"),
}

_VALIDATION = _re.compile(r"^Validation failed on .*$")


# ------------------------------------------------------------------------------
# Data
# ------------------------------------------------------------------------------


@_dataclasses.dataclass(frozen=True)
class Phase:
    # BabelStream 5.0 swaps the two timings: the value it labels Init is the
    # time for reading the arrays back, and vice versa. The labels are kept
    # as printed so that the data can be compared with other BabelStream runs.
    name: str
    n_elements: int
    element_bytes: int
    bandwidth_mb_per_s: float
    runtime_s: float


@_dataclasses.dataclass(frozen=True)
class Kernel:
    name: str
    numtimes: int
    n_elements: int
    element_bytes: int
    bandwidth_max_mb_per_s: float
    runtime_min_s: float
    runtime_max_s: float
    runtime_avg_s: float

    @property
    def bytes_per_iteration(self) -> int:
        return KERNEL_ARRAYS[self.name] * self.n_elements * self.element_bytes

    @property
    def bandwidth_avg_mb_per_s(self) -> float:
        # BabelStream reports only the best bandwidth. The benchmark
        # description asks for the average, derived here from the same byte
        # count and the average runtime (first iteration excluded, as in
        # BabelStream).
        return 1.0e-6 * self.bytes_per_iteration / self.runtime_avg_s


@_dataclasses.dataclass(frozen=True)
class Output:
    phases: list[Phase]
    kernels: list[Kernel]
    device: dict[str, str]
    validation_errors: list[str]


# ------------------------------------------------------------------------------
# Parsing
# ------------------------------------------------------------------------------


def _split(*, line: str) -> tuple[str, ...]:
    return tuple(field.strip() for field in line.split(","))


def _check_header(*, fields: tuple[str, ...], expected: tuple[str, ...]):
    if fields != expected:
        raise ValueError(
            f"unexpected BabelStream table header {','.join(fields)!r}; "
            f"expected {','.join(expected)!r} (was --mibibytes or "
            "--triad-only passed?)"
        )


def _phase(*, fields: tuple[str, ...]) -> Phase:
    return Phase(
        name=fields[0],
        n_elements=int(fields[1]),
        element_bytes=int(fields[2]),
        bandwidth_mb_per_s=float(fields[3]),
        runtime_s=float(fields[4]),
    )


def _kernel(*, fields: tuple[str, ...]) -> Kernel:
    if fields[0] not in KERNEL_ARRAYS:
        raise ValueError(f"unknown BabelStream kernel {fields[0]!r}")
    return Kernel(
        name=fields[0],
        numtimes=int(fields[1]),
        n_elements=int(fields[2]),
        element_bytes=int(fields[3]),
        bandwidth_max_mb_per_s=float(fields[4]),
        runtime_min_s=float(fields[5]),
        runtime_max_s=float(fields[6]),
        runtime_avg_s=float(fields[7]),
    )


def parse(*, stdout: str, stderr: str) -> Output:
    phases = []
    kernels = []
    device = {}
    table = None

    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue

        fields = _split(line=line)
        if fields[0] == "phase":
            _check_header(fields=fields, expected=_PHASE_HEADER)
            table = "phase"
            continue
        if fields[0] == "function":
            _check_header(fields=fields, expected=_KERNEL_HEADER)
            table = "kernel"
            continue

        if table == "phase" and len(fields) == len(_PHASE_HEADER):
            phases.append(_phase(fields=fields))
            continue
        if table == "kernel" and len(fields) == len(_KERNEL_HEADER):
            kernels.append(_kernel(fields=fields))
            continue

        # Anything else is a free-form line; it also ends the current table.
        table = None
        for key, pattern in _DEVICE_PATTERNS.items():
            match = pattern.match(line)
            if match is not None:
                device[key] = match["value"].strip()

    validation_errors = [
        line.strip()
        for line in stderr.splitlines()
        if _VALIDATION.match(line.strip())
    ]

    return Output(
        phases=phases,
        kernels=kernels,
        device=device,
        validation_errors=validation_errors,
    )
