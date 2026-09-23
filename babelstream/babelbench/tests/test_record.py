# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------

import json as _json
import pathlib as _pathlib

import babelbench.cli
import babelbench.record
import babelbench.report

DATA = _pathlib.Path(__file__).parent / "data"
STDOUT = (DATA / "omp-stream.out").read_text()


def _record(*, key: str, threads: int, stdout: str, stderr: str) -> dict:
    return babelbench.record.build(
        key=key,
        model="omp",
        threads=threads,
        array_size=2**28,
        numtimes=100,
        stdout=stdout,
        stderr=stderr,
        metadata={"node": "jrc0001", "jobid": "4711"},
    )


def test_record_and_report(tmp_path):
    artifacts = tmp_path / "artifacts"
    for threads in (1, 16, 128):
        record = _record(
            key=f"omp-t{threads:03d}", threads=threads, stdout=STDOUT, stderr=""
        )
        assert record["status"]["success"]
        assert record["parameters"]["exponent"] == 28
        babelbench.record.store(record=record, files=[], artifacts=artifacts)

    failed = _record(
        key="omp-t004",
        threads=4,
        stdout=STDOUT,
        stderr="Validation failed on a[]. Average error 1.5\n",
    )
    assert not failed["status"]["success"]
    assert "Validation failed" in failed["status"]["problems"][0]
    babelbench.record.store(record=failed, files=[], artifacts=artifacts)

    results = babelbench.report.write(artifacts=artifacts)
    assert len(results["records"]) == 4
    assert (artifacts / "plots" / "threads-omp-e28.svg").is_file()
    assert (artifacts / "plots" / "threads-omp-e28.png").is_file()
    summary = (artifacts / "summary.md").read_text()
    assert "4 runs, 1 failed" in summary
    assert "omp-t004" in summary
    assert "jrc0001" in summary
    rows = (artifacts / "results.csv").read_text().splitlines()
    # One header plus five kernels per run; the failed run still has results,
    # flagged by its success column.
    assert len(rows) == 1 + 4 * 5
    assert sum(",False," in row for row in rows) == 5


def test_output_must_match_the_stated_run():
    record = babelbench.record.build(
        key="wrong-size",
        model="omp",
        threads=1,
        array_size=2**20,
        numtimes=100,
        stdout=STDOUT,
        stderr="",
        metadata={},
    )
    assert not record["status"]["success"]
    assert "expected 1048576" in record["status"]["problems"][0]


def test_missing_output_is_a_failed_record(tmp_path):
    record = _record(key="empty", threads=1, stdout="", stderr="")
    assert record["status"]["problems"] == ["no kernel results in output"]


def test_command_line(tmp_path):
    stdout = tmp_path / "job.out"
    stdout.write_text(STDOUT)
    script = tmp_path / "submit.job"
    script.write_text("#!/bin/bash\n")
    artifacts = tmp_path / "artifacts"
    status = babelbench.cli.main(
        argv=[
            "record",
            "--artifacts", str(artifacts),
            "--key", "omp-t128",
            "--model", "omp",
            "--threads", "128",
            "--array-size", str(2**28),
            "--numtimes", "100",
            "--stdout", str(stdout),
            "--stderr", str(tmp_path / "missing.err"),
            "--metadata", "node=jrc0001",
            "--metadata", "partition=dc-cpu-devel",
            "--file", str(script),
            "--file", str(tmp_path / "missing.lock"),
        ]
    )  # fmt: skip
    assert status == 0
    record = _json.loads((artifacts / "records" / "omp-t128.json").read_text())
    assert record["metadata"] == {
        "node": "jrc0001",
        "partition": "dc-cpu-devel",
    }
    assert (artifacts / "raw" / "omp-t128" / "submit.job").is_file()
    assert not (artifacts / "raw" / "omp-t128" / "missing.lock").exists()


def test_schema_lists_every_record_key():
    record = _record(key="k", threads=1, stdout=STDOUT, stderr="")
    schema_path = (
        _pathlib.Path(babelbench.record.__file__).parent
        / "share"
        / "record.schema.json"
    )
    schema = _json.loads(schema_path.read_text())
    assert set(schema["required"]) == set(record)
    assert schema["properties"]["schema"]["const"] == record["schema"]
