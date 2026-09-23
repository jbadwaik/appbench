<!--
  ============================================================================
  SPDX-FileCopyrightText: ADAC Contributors
  SPDX-License-Identifier: Apache-2.0
  ============================================================================
-->

# babelbench

Turns the output of [BabelStream](https://github.com/UoB-HPC/BabelStream)
runs into JSON records, a CSV table, plots and a Markdown summary. It knows
nothing about the framework that ran BabelStream: JUBE, ReFrame, a batch
script or a shell loop can all call it the same way.

## Commands

```bash
# Once per campaign: git commit, system and tool versions
babelbench context --root REPOSITORY --output context.json

# Once per run, after BabelStream finished
babelbench record --artifacts DIR --key KEY --model MODEL \
    --threads N --array-size N --numtimes N \
    --stdout FILE --stderr FILE \
    [--metadata NAME=VALUE ...] [--file FILE ...]

# Any time: aggregate every record in DIR
babelbench report --artifacts DIR
```

`record` needs BabelStream to have run with `--csv`. The caller states what
ran: the programming model, the thread count, the array size and the number
of iterations. The record checks that BabelStream's output agrees, and fails
the run if it reports validation errors, which BabelStream itself does not
signal through its exit status.

`--key` names the run and must be unique in the artifact directory.
`--metadata` keeps free-form strings, such as `node=...` or `jobid=...`; the
summary shows `node` when present. `--file` copies files next to the record,
such as the job script; missing files are skipped.

`record` exits with 1 when the run failed, after writing the record, so the
calling framework can flag it. `report` can run after every record: it
rebuilds everything from the records in the directory.

## Output

```
DIR/
  context.json        written by the caller, from `babelbench context`
  records/<key>.json  one per run, see src/babelbench/share/record.schema.json
  raw/<key>/          the files passed with --file
  results.json        context and all records
  results.csv         one row per run and kernel
  summary.md          tables per model, best average triad, failures, plots
  plots/              bandwidth against threads or array size, SVG and PNG
```

Bandwidths are in MB/s with MB = 10^6 bytes, as BabelStream reports them.
Each kernel has the best bandwidth, from the minimum runtime, and the average
bandwidth, from the average runtime, both excluding the first iteration.

BabelStream 5.0 swaps the labels of its Init and Read timings. Records keep
the labels as printed, for comparability with other BabelStream data.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```
