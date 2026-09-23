# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Turn the output of one BabelStream run into a JSON record.

Nothing here knows which framework ran BabelStream. The caller says what ran
(model, threads, array size, iterations), where the output is, and anything
else worth keeping as free-form metadata, such as the node or the job id.
"""

import json as _json
import pathlib as _pathlib
import shutil as _shutil

import babelbench.parse

SCHEMA = "babelbench.record/2"

# ------------------------------------------------------------------------------
# Record
# ------------------------------------------------------------------------------


def _kernel(*, kernel: babelbench.parse.Kernel) -> dict:
    return {
        "name": kernel.name,
        "numtimes": kernel.numtimes,
        "n_elements": kernel.n_elements,
        "element_bytes": kernel.element_bytes,
        "bytes_per_iteration": kernel.bytes_per_iteration,
        "bandwidth_max_mb_per_s": kernel.bandwidth_max_mb_per_s,
        "bandwidth_avg_mb_per_s": kernel.bandwidth_avg_mb_per_s,
        "runtime_min_s": kernel.runtime_min_s,
        "runtime_max_s": kernel.runtime_max_s,
        "runtime_avg_s": kernel.runtime_avg_s,
    }


def _phase(*, phase: babelbench.parse.Phase) -> dict:
    return {
        "name": phase.name,
        "n_elements": phase.n_elements,
        "element_bytes": phase.element_bytes,
        "bandwidth_mb_per_s": phase.bandwidth_mb_per_s,
        "runtime_s": phase.runtime_s,
    }


def _parse(*, stdout: str, stderr: str) -> tuple[babelbench.parse.Output, list]:
    try:
        return babelbench.parse.parse(stdout=stdout, stderr=stderr), []
    except ValueError as error:
        empty = babelbench.parse.Output(
            phases=[], kernels=[], device={}, validation_errors=[]
        )
        return empty, [f"unparsable output: {error}"]


def _consistency(
    *, output: babelbench.parse.Output, array_size: int, numtimes: int
) -> list[str]:
    # The output must describe the run the caller says it was.
    problems = []
    for kernel in output.kernels:
        if kernel.n_elements != array_size:
            problems.append(
                f"{kernel.name} ran with {kernel.n_elements} elements, "
                f"expected {array_size}"
            )
        if kernel.numtimes != numtimes:
            problems.append(
                f"{kernel.name} ran {kernel.numtimes} times, "
                f"expected {numtimes}"
            )
    return problems


def build(
    *,
    key: str,
    model: str,
    threads: int,
    array_size: int,
    numtimes: int,
    stdout: str,
    stderr: str,
    metadata: dict[str, str],
) -> dict:
    output, problems = _parse(stdout=stdout, stderr=stderr)
    if not output.kernels and not problems:
        problems.append("no kernel results in output")
    problems.extend(
        _consistency(output=output, array_size=array_size, numtimes=numtimes)
    )
    problems.extend(output.validation_errors)

    return {
        "schema": SCHEMA,
        "key": key,
        "parameters": {
            "model": model,
            "threads": threads,
            "array_size": array_size,
            "exponent": array_size.bit_length() - 1,
            "numtimes": numtimes,
        },
        "metadata": metadata,
        "status": {"success": not problems, "problems": problems},
        "device": output.device,
        "phases": [_phase(phase=phase) for phase in output.phases],
        "kernels": [_kernel(kernel=kernel) for kernel in output.kernels],
    }


def store(
    *,
    record: dict,
    files: list[_pathlib.Path],
    artifacts: _pathlib.Path,
) -> _pathlib.Path:
    records = artifacts / "records"
    records.mkdir(parents=True, exist_ok=True)
    path = records / f"{record['key']}.json"
    path.write_text(_json.dumps(record, indent=2) + "\n")

    # Files worth keeping with the record, such as the job script or build
    # provenance. Missing ones are skipped: not every build leaves the same.
    raw = artifacts / "raw" / record["key"]
    for source in files:
        if source.is_file():
            raw.mkdir(parents=True, exist_ok=True)
            _shutil.copyfile(source, raw / source.name)
    return path
