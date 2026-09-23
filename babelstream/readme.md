<!--
  ============================================================================
  SPDX-FileCopyrightText: ADAC Contributors
  SPDX-License-Identifier: Apache-2.0
  ============================================================================
-->

# babelstream

Memory bandwidth of a single node with
[BabelStream](https://github.com/UoB-HPC/BabelStream), run through JUBE on
JURECA-DC.

## Environment

| Variable                 | When          | Value                            |
| ------------------------ | ------------- | -------------------------------- |
| `BUDGET_ACCOUNTS`        | always        | budget the jobs are charged to   |
| `JUBE_ARTIFACT_DIR`      | always        | absolute path for the results    |
| `JUBE_INCLUDE_PATH`      | always        | JUBE `platform/slurm` directory  |
| `BABELBENCH_SPACK_STORE` | `--tag spack` | directory Spack installs into    |

Nothing has a default: `jube run` stops at once if a variable it needs is
missing. `JUBE_ARTIFACT_DIR` must be absolute, since every JUBE step runs in
its own directory and a relative path scatters the results across them.
`BUDGET_ACCOUNTS` becomes the Slurm `--account` of every job.
`JUBE_INCLUDE_PATH` lets JUBE find its standard `platform.xml`; the JUBE
module on JSC systems usually sets it, otherwise point it at
`share/jube/platform/slurm` of your JUBE installation.

## Running

From this directory, on a login node:

```bash
jutil env activate -p <project>
module load JUBE

export BUDGET_ACCOUNTS=<budget>
export JUBE_ARTIFACT_DIR=$SCRATCH/babelstream-results
# only if the JUBE module does not set it
export JUBE_INCLUDE_PATH=$EBROOTJUBE/share/jube/platform/slurm
# only for --tag spack
export BABELBENCH_SPACK_STORE=$PROJECT/babelstream-spack

jube run jube/benchmark.yaml
jube continue jube/runs      # repeat until every step is done
jube status jube/runs
```

The build downloads BabelStream from GitHub and compiles it, so the login
node needs internet access. It also loads the `uv` module, which runs the
post-processing.

| Tags        | What runs                                           | Jobs |
| ----------- | --------------------------------------------------- | ---: |
| (none)      | OpenMP, 128 threads, 2^28 elements                  |    1 |
| `full`      | OpenMP, 1 to 128 threads x 2^16 to 2^30 elements    |   64 |
| `cuda`      | CUDA on one GPU, 2^28 elements                      |    1 |
| `cuda full` | CUDA on one GPU, 2^16 to 2^30 elements              |    8 |

Tags combine, e.g. `jube run jube/benchmark.yaml --tag cuda full`. Add
`--tag spack` to build BabelStream with Spack instead of from source.

## Results

```bash
ls $JUBE_ARTIFACT_DIR/babelstream-000000/    # 000000 is the JUBE run id
```

`summary.md` has the bandwidth tables, `results.csv` one row per run and
kernel, and `records/` one JSON file per job.

## When a step fails

Each step's output is in `jube/runs/<run id>/<workpackage>_<step>/work/`,
in `stdout` and `stderr`. After fixing the cause, delete the step's `error`
file and continue:

```bash
rm jube/runs/000000/000001_setup/error
jube continue jube/runs
```

Changes to the YAML files only apply to a new `jube run`.

More detail: `jube/readme.md` for the benchmark, `babelbench/readme.md` for
the post-processing.
