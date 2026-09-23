# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------
"""Aggregate all records in an artifact directory into the final report.

The report is rebuilt from scratch from `records/` every time, so it can be
regenerated after every job and is complete once the last job is recorded.
"""

import collections as _collections
import csv as _csv
import json as _json
import pathlib as _pathlib

SCHEMA = "babelbench.results/1"

# The headline metric: the benchmark description asks for the average triad
# bandwidth.
HEADLINE_KERNEL = "Triad"

KERNELS = ("Copy", "Mul", "Add", "Triad", "Dot")

CSV_COLUMNS = (
    "key",
    "success",
    "model",
    "threads",
    "exponent",
    "array_size",
    "numtimes",
    "node",
    "jobid",
    "kernel",
    "bandwidth_avg_mb_per_s",
    "bandwidth_max_mb_per_s",
    "runtime_min_s",
    "runtime_max_s",
    "runtime_avg_s",
)

# ------------------------------------------------------------------------------
# Loading
# ------------------------------------------------------------------------------


def _load(*, artifacts: _pathlib.Path) -> tuple[dict | None, list[dict]]:
    context_path = artifacts / "context.json"
    context = (
        _json.loads(context_path.read_text())
        if context_path.is_file()
        else None
    )
    records = [
        _json.loads(path.read_text())
        for path in sorted((artifacts / "records").glob("*.json"))
    ]
    return context, records


def _headline(*, record: dict) -> dict | None:
    for kernel in record["kernels"]:
        if kernel["name"] == HEADLINE_KERNEL:
            return kernel
    return None


# ------------------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------------------


def _write_csv(*, records: list[dict], path: _pathlib.Path):
    with path.open("w", newline="") as stream:
        writer = _csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            parameters = record["parameters"]
            for kernel in record["kernels"]:
                writer.writerow(
                    {
                        "key": record["key"],
                        "success": record["status"]["success"],
                        "model": parameters["model"],
                        "threads": parameters["threads"],
                        "exponent": parameters["exponent"],
                        "array_size": parameters["array_size"],
                        "numtimes": parameters["numtimes"],
                        "node": record["metadata"].get("node"),
                        "jobid": record["metadata"].get("jobid"),
                        "kernel": kernel["name"],
                        "bandwidth_avg_mb_per_s": kernel[
                            "bandwidth_avg_mb_per_s"
                        ],
                        "bandwidth_max_mb_per_s": kernel[
                            "bandwidth_max_mb_per_s"
                        ],
                        "runtime_min_s": kernel["runtime_min_s"],
                        "runtime_max_s": kernel["runtime_max_s"],
                        "runtime_avg_s": kernel["runtime_avg_s"],
                    }
                )


def _gb(*, mb: float) -> str:
    return f"{mb / 1000.0:.1f}"


def _summary(
    *, context: dict | None, records: list[dict], plots: list[str]
) -> str:
    lines = ["# BabelStream", ""]

    if context is not None:
        repository = context["repository"]
        commit = repository.get("commit", "unknown")
        dirty = " (dirty)" if repository.get("dirty") else ""
        lines += [
            f"- system: {context['system']['name'] or 'unknown'}",
            f"- captured: {context['created']}",
            f"- repository: `{commit}`{dirty}",
            "",
        ]

    failed = [record for record in records if not record["status"]["success"]]
    lines += [
        f"{len(records)} runs, {len(failed)} failed. Bandwidths in GB/s "
        "(10^9 bytes); average over iterations 2..n, best in brackets.",
        "",
    ]

    by_model = _collections.defaultdict(list)
    for record in records:
        by_model[record["parameters"]["model"]].append(record)

    for model, group in sorted(by_model.items()):
        lines += [
            f"## {model}",
            "",
            "| threads | 2^e | Copy | Mul | Add | Triad | Dot | node |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
        ordered = sorted(
            group,
            key=lambda record: (
                record["parameters"]["exponent"],
                record["parameters"]["threads"],
            ),
        )
        for record in ordered:
            cells = {
                kernel["name"]: (
                    f"{_gb(mb=kernel['bandwidth_avg_mb_per_s'])} "
                    f"({_gb(mb=kernel['bandwidth_max_mb_per_s'])})"
                )
                for kernel in record["kernels"]
            }
            if not record["status"]["success"]:
                cells = {name: "failed" for name in KERNELS}
            parameters = record["parameters"]
            lines.append(
                f"| {parameters['threads']} | {parameters['exponent']} | "
                + " | ".join(cells.get(name, "") for name in KERNELS)
                + f" | {record['metadata'].get('node', '')} |"
            )

        best = max(
            (
                record
                for record in group
                if record["status"]["success"] and _headline(record=record)
            ),
            key=lambda record: _headline(record=record)[
                "bandwidth_avg_mb_per_s"
            ],
            default=None,
        )
        if best is not None:
            headline = _headline(record=best)
            lines += [
                "",
                f"Best average {HEADLINE_KERNEL}: "
                f"**{_gb(mb=headline['bandwidth_avg_mb_per_s'])} GB/s** "
                f"with {best['parameters']['threads']} threads at "
                f"2^{best['parameters']['exponent']} elements.",
            ]
        lines.append("")

    if failed:
        lines += ["## Failures", ""]
        for record in failed:
            problems = "; ".join(record["status"]["problems"])
            lines.append(f"- `{record['key']}`: {problems}")
        lines.append("")

    if plots:
        lines += ["## Plots", ""]
        lines += [f"![{plot}](plots/{plot})" for plot in plots]
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------------------
# Plots
# ------------------------------------------------------------------------------


def _plot_series(
    *,
    records: list[dict],
    axis: str,
    label: str,
    logarithmic: bool,
    title: str,
    path: _pathlib.Path,
):
    # Imported here so that parsing and recording work without a display
    # backend being configured.
    import matplotlib as _matplotlib

    _matplotlib.use("Agg")
    import matplotlib.pyplot as _pyplot

    ordered = sorted(records, key=lambda record: record["parameters"][axis])
    names = [kernel["name"] for kernel in ordered[0]["kernels"]]

    figure, axes = _pyplot.subplots(figsize=(7, 4.5))
    for name in names:
        xs = []
        ys = []
        for record in ordered:
            for kernel in record["kernels"]:
                if kernel["name"] == name:
                    xs.append(record["parameters"][axis])
                    ys.append(kernel["bandwidth_avg_mb_per_s"] / 1000.0)
        axes.plot(xs, ys, marker="o", label=name)

    if logarithmic:
        axes.set_xscale("log", base=2)
    if axis == "threads":
        values = sorted({record["parameters"][axis] for record in ordered})
        axes.set_xticks(values, labels=[str(value) for value in values])
    # Bandwidths are compared by ratio, so the axis starts at zero.
    axes.set_ylim(0, axes.get_ylim()[1] * 1.05)
    axes.set_xlabel(label)
    axes.set_ylabel("Average bandwidth / GB/s")
    axes.set_title(title)
    axes.grid(visible=True, alpha=0.3)
    axes.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(path.with_suffix(".svg"))
    figure.savefig(path.with_suffix(".png"), dpi=150)
    _pyplot.close(figure)


def _plots(*, records: list[dict], directory: _pathlib.Path) -> list[str]:
    good = [
        record
        for record in records
        if record["status"]["success"] and record["kernels"]
    ]
    directory.mkdir(parents=True, exist_ok=True)
    produced = []

    # Bandwidth against thread count, one plot per model and array size.
    by_size = _collections.defaultdict(list)
    for record in good:
        parameters = record["parameters"]
        by_size[(parameters["model"], parameters["exponent"])].append(record)
    for (model, exponent), group in sorted(by_size.items()):
        if len({record["parameters"]["threads"] for record in group}) < 2:
            continue
        name = f"threads-{model}-e{exponent:02d}"
        _plot_series(
            records=group,
            axis="threads",
            label="OpenMP threads",
            logarithmic=True,
            title=f"BabelStream {model}, 2^{exponent} elements",
            path=directory / name,
        )
        produced.append(f"{name}.svg")

    # Bandwidth against array size, one plot per model and thread count.
    by_threads = _collections.defaultdict(list)
    for record in good:
        parameters = record["parameters"]
        by_threads[(parameters["model"], parameters["threads"])].append(record)
    for (model, threads), group in sorted(by_threads.items()):
        if len({record["parameters"]["exponent"] for record in group}) < 2:
            continue
        name = f"sizes-{model}-t{threads:03d}"
        _plot_series(
            records=group,
            axis="array_size",
            label="Elements per array",
            logarithmic=True,
            title=f"BabelStream {model}, {threads} threads",
            path=directory / name,
        )
        produced.append(f"{name}.svg")

    return produced


# ------------------------------------------------------------------------------
# Report
# ------------------------------------------------------------------------------


def write(*, artifacts: _pathlib.Path) -> dict:
    context, records = _load(artifacts=artifacts)

    plots = _plots(records=records, directory=artifacts / "plots")

    results = {
        "schema": SCHEMA,
        "context": context,
        "headline_kernel": HEADLINE_KERNEL,
        "records": records,
    }
    (artifacts / "results.json").write_text(
        _json.dumps(results, indent=2) + "\n"
    )
    _write_csv(records=records, path=artifacts / "results.csv")
    (artifacts / "summary.md").write_text(
        _summary(context=context, records=records, plots=plots)
    )
    return results
