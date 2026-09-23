# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Capture the provenance of a benchmark run before any job is submitted.

Every probe is allowed to fail: a missing tool is recorded as such rather
than aborting the run, since the context is descriptive, not a precondition.
"""

import datetime as _datetime
import os as _os
import pathlib as _pathlib
import platform as _platform
import shutil as _shutil
import socket as _socket
import subprocess as _subprocess

import babelbench.metadata

SCHEMA = "babelbench.context/1"

# ------------------------------------------------------------------------------
# Probes
# ------------------------------------------------------------------------------


def _command(*, argv: list[str], cwd: _pathlib.Path) -> dict:
    if _shutil.which(argv[0]) is None:
        return {"argv": argv, "available": False}
    try:
        result = _subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except _subprocess.TimeoutExpired:
        return {"argv": argv, "available": True, "timeout": True}
    return {
        "argv": argv,
        "available": True,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
    }


def _read(*, path: _pathlib.Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _os_release() -> dict[str, str]:
    text = _read(path=_pathlib.Path("/etc/os-release"))
    if text is None:
        return {}
    entries = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            entries[key] = value.strip('"')
    return entries


def _git(*, root: _pathlib.Path) -> dict:
    commit = _command(argv=["git", "rev-parse", "HEAD"], cwd=root)
    status = _command(argv=["git", "status", "--porcelain"], cwd=root)
    if commit.get("returncode") != 0:
        return {"available": False}
    return {
        "available": True,
        "commit": commit["stdout"],
        "dirty": bool(status.get("stdout")),
    }


def _tool_version(*, argv: list[str], root: _pathlib.Path) -> str | None:
    result = _command(argv=argv, cwd=root)
    if result.get("returncode") != 0:
        return None
    return result["stdout"].splitlines()[0] if result["stdout"] else ""


# ------------------------------------------------------------------------------
# Context
# ------------------------------------------------------------------------------


def capture(*, root: _pathlib.Path) -> dict:
    now = _datetime.datetime.now(tz=_datetime.UTC)
    os_release = _os_release()
    return {
        "schema": SCHEMA,
        "created": now.isoformat(timespec="seconds"),
        "babelbench": babelbench.metadata.__version__,
        "system": {
            # JSC systems publish their name here; JURECA-DC reports jurecadc.
            "name": _read(path=_pathlib.Path("/etc/FZJ/systemname")),
            "login_host": _socket.gethostname(),
            "os": os_release.get("PRETTY_NAME"),
            "kernel": _platform.release(),
            "machine": _platform.machine(),
        },
        "user": {
            "budget": _os.environ.get("BUDGET_ACCOUNTS"),
        },
        "repository": _git(root=root),
        "tools": {
            "python": _platform.python_version(),
            "jube": _tool_version(argv=["jube", "--version"], root=root),
            "spack": _tool_version(argv=["spack", "--version"], root=root),
            "uv": _tool_version(argv=["uv", "--version"], root=root),
            "slurm": _tool_version(argv=["sbatch", "--version"], root=root),
        },
    }
