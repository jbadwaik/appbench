# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Command line interface, usable from any benchmarking framework.

babelbench context --root DIR --output FILE
babelbench record --artifacts DIR --key KEY --model MODEL
                  --threads N --array-size N --numtimes N
                  --stdout FILE --stderr FILE
                  [--metadata NAME=VALUE ...] [--file FILE ...]
babelbench report --artifacts DIR

`context` describes the machine and repository once per campaign, `record`
turns one run into a JSON record, and `report` aggregates all records.
"""

import argparse as _argparse
import json as _json
import pathlib as _pathlib
import sys as _sys

import babelbench.context
import babelbench.metadata
import babelbench.record
import babelbench.report

# ------------------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------------------


def _context(*, arguments: _argparse.Namespace) -> int:
    context = babelbench.context.capture(root=arguments.root.resolve())
    arguments.output.write_text(_json.dumps(context, indent=2) + "\n")
    return 0


def _metadata(*, entries: list[str] | None) -> dict[str, str]:
    metadata = {}
    for entry in entries or []:
        name, separator, value = entry.partition("=")
        if not separator or not name:
            raise SystemExit(f"--metadata expects NAME=VALUE, got {entry!r}")
        metadata[name] = value
    return metadata


def _read(*, path: _pathlib.Path) -> str:
    # A missing output file is recorded as a failed run, not an error here.
    try:
        return path.read_text()
    except OSError:
        return ""


def _record(*, arguments: _argparse.Namespace) -> int:
    record = babelbench.record.build(
        key=arguments.key,
        model=arguments.model,
        threads=arguments.threads,
        array_size=arguments.array_size,
        numtimes=arguments.numtimes,
        stdout=_read(path=arguments.stdout),
        stderr=_read(path=arguments.stderr),
        metadata=_metadata(entries=arguments.metadata),
    )
    path = babelbench.record.store(
        record=record,
        files=arguments.file or [],
        artifacts=arguments.artifacts,
    )
    print(f"{record['key']}: {path}")
    if record["status"]["success"]:
        return 0
    # The record is written either way; the exit status tells the caller.
    for problem in record["status"]["problems"]:
        print(f"{record['key']}: {problem}", file=_sys.stderr)
    return 1


def _report(*, arguments: _argparse.Namespace) -> int:
    results = babelbench.report.write(artifacts=arguments.artifacts)
    print(
        f"{len(results['records'])} records reported in "
        f"{arguments.artifacts / 'summary.md'}"
    )
    return 0


# ------------------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------------------


def _parser() -> _argparse.ArgumentParser:
    parser = _argparse.ArgumentParser(
        prog="babelbench",
        description="Turn BabelStream output into records, tables and plots.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=babelbench.metadata.__version__,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    context = commands.add_parser(
        "context", help="capture the provenance of a benchmark run"
    )
    context.add_argument("--root", type=_pathlib.Path, required=True)
    context.add_argument("--output", type=_pathlib.Path, required=True)
    context.set_defaults(handler=_context)

    record = commands.add_parser(
        "record", help="turn the output of one run into a JSON record"
    )
    record.add_argument("--artifacts", type=_pathlib.Path, required=True)
    record.add_argument("--key", required=True, help="unique name of the run")
    record.add_argument("--model", required=True, help="omp, cuda, ...")
    record.add_argument("--threads", type=int, required=True)
    record.add_argument("--array-size", type=int, required=True)
    record.add_argument("--numtimes", type=int, required=True)
    record.add_argument("--stdout", type=_pathlib.Path, required=True)
    record.add_argument("--stderr", type=_pathlib.Path, required=True)
    record.add_argument(
        "--metadata",
        action="append",
        metavar="NAME=VALUE",
        help="free-form information to keep, repeatable",
    )
    record.add_argument(
        "--file",
        action="append",
        type=_pathlib.Path,
        help="file to keep next to the record, repeatable",
    )
    record.set_defaults(handler=_record)

    report = commands.add_parser(
        "report", help="aggregate all records into results and plots"
    )
    report.add_argument("--artifacts", type=_pathlib.Path, required=True)
    report.set_defaults(handler=_report)

    return parser


def main(*, argv: list[str]) -> int:
    arguments = _parser().parse_args(argv)
    return arguments.handler(arguments=arguments)


def entry():
    raise SystemExit(main(argv=_sys.argv[1:]))
