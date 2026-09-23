# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------

import pathlib as _pathlib

import pytest as _pytest

import babelbench.metadata
import babelbench.parse

DATA = _pathlib.Path(__file__).parent / "data"


def _output(*, name: str, stderr: str) -> babelbench.parse.Output:
    return babelbench.parse.parse(
        stdout=(DATA / name).read_text(), stderr=stderr
    )


def test_omp_tables():
    output = _output(name="omp-stream.out", stderr="")
    assert [phase.name for phase in output.phases] == ["Init", "Read"]
    assert [kernel.name for kernel in output.kernels] == [
        "Copy",
        "Mul",
        "Add",
        "Triad",
        "Dot",
    ]
    assert output.device == {}
    assert output.validation_errors == []


def test_average_bandwidth_uses_babelstream_byte_count():
    output = _output(name="omp-stream.out", stderr="")
    triad = output.kernels[3]
    assert triad.bytes_per_iteration == 3 * 8 * 2**28
    # The reported best bandwidth follows from the same byte count.
    best = 1.0e-6 * triad.bytes_per_iteration / triad.runtime_min_s
    assert best == _pytest.approx(triad.bandwidth_max_mb_per_s, rel=1.0e-4)
    assert triad.bandwidth_avg_mb_per_s < triad.bandwidth_max_mb_per_s


def test_cuda_device_lines():
    output = _output(name="cuda-stream.out", stderr="")
    assert output.device == {
        "name": "NVIDIA A100-SXM4-40GB",
        "driver": "12040",
        "memory_mode": "DEFAULT",
    }
    assert len(output.kernels) == 5


def test_validation_failure_on_stderr():
    stderr = "Validation failed on a[]. Average error 1.5\nother noise\n"
    output = _output(name="omp-stream.out", stderr=stderr)
    assert output.validation_errors == [
        "Validation failed on a[]. Average error 1.5"
    ]


def test_mibibytes_is_rejected():
    stdout = "function,num_times,n_elements,sizeof,max_mibytes_per_sec\n"
    with _pytest.raises(ValueError, match="mibibytes"):
        babelbench.parse.parse(stdout=stdout, stderr="")


def test_semver():
    version = babelbench.metadata.parse_semver(text="1.2.3-rc.1+abc")
    assert (version.major, version.minor, version.patch) == (1, 2, 3)
    assert version.prerelease == "rc.1"
    assert version.build == "abc"
