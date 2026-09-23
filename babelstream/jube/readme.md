<!--
  ============================================================================
  SPDX-FileCopyrightText: ADAC Contributors
  SPDX-License-Identifier: Apache-2.0
  ============================================================================
-->

# BabelStream with JUBE

Runs BabelStream through [JUBE](https://github.com/FZJ-JSC/JUBE): one
Slurm job per configuration, with JUBE's standard Slurm platform, and
`babelbench` (`../babelbench`) turning the output into records, tables and
plots.

| Platform  | Platform file          | CPU runs         | GPU runs      |
| --------- | ---------------------- | ---------------- | ------------- |
| JURECA-DC | `platform.jureca.yaml` | 2x AMD EPYC 7742 | 1 NVIDIA A100 |

JUBE's `platform.xml` is used as shipped. Everything specific to a system
is layered on top of it in a platform file, and nothing else in this
directory is system-specific. A platform file provides:

- `environment`: the shell command that sets up the compiler and tools,
  used by both builds and by the jobs; on JURECA-DC, a JSC software stage
  with GCC, CMake and, for `--tag cuda`, CUDA
- `cuda_arch`: the compute capability of the GPUs
- `executeset` and `systemParameter`: partitions, budget, time limits and
  CPU pinning for the Slurm jobs

The platform is chosen in `babelstream.yaml`, in the `environment` set and
the execute step.

## Running on JURECA-DC

From the repository root on a JURECA login node, with Spack for
`--tag spack`:

```bash
jutil env activate -p <project>      # sets BUDGET_ACCOUNTS
module load JUBE
export JUBE_ARTIFACT_DIR=$SCRATCH/babelstream
export BABELBENCH_SPACK_STORE=$PROJECT/spack-store   # --tag spack only
jube run jube/babelstream.yaml [--tag cuda] [--tag full] [--tag spack]
jube continue jube/runs              # repeat until every step is done
```

JUBE finds `platform.xml` through `JUBE_INCLUDE_PATH`, which the JUBE module
on JSC systems sets. Elsewhere, point it at the `share/jube/platform/slurm`
directory of your JUBE installation.

`JUBE_ARTIFACT_DIR` is always required, and `BABELBENCH_SPACK_STORE` for the
Spack build; the run stops at once if one is missing.
`JUBE_ARTIFACT_DIR` must be an absolute path, since every step runs in its
own workpackage directory. On JURECA, put the Spack store on a project file
system, since home quotas are small.

## Building

There are two build files:

- `build.easybuild.yaml`, the default, builds BabelStream from its release
  tarball with the compiler and tools of the platform's EasyBuild modules.
- `build.spack.yaml`, selected with `--tag spack`, builds BabelStream
  with Spack from `../spack/spack.yaml` into `BABELBENCH_SPACK_STORE`.

Each has a step named `build` that writes the path of BabelStream's
executable to `executable.txt`, and a script `tools.sh` that makes uv
available: the EasyBuild build loads the `uv` module, the Spack build adds
`py-uv` to its environment. The setup and postprocess steps source it before
running babelbench. A build of your own needs the same two files.

The EasyBuild build sets up the platform's environment, downloads the
BabelStream release from GitHub, checks its SHA-256, and builds and
installs it with CMake into the build workpackage. The CUDA build uses
`nvcc` from the environment and the platform's `cuda_arch`. The release,
its checksum and the CMake options are at the top of `build.easybuild.yaml`.
Like the Spack build, it keeps BabelStream's default `-O3 -march=native`.

The Spack build sets up the platform's environment, registers the compiler
and tools it finds there, and installs `babelstream +omp`, or
`babelstream +cuda cuda_arch=<cuda_arch>`. Anything the environment does not
provide, Spack builds itself.

## Run modes

| Tags        | Model | Threads       | Elements per array | Jobs |
| ----------- | ----- | ------------- | ------------------ | ---: |
| (none)      | omp   | 128           | 2^28               |    1 |
| `full`      | omp   | 1, 2, 4 … 128 | 2^16, 2^18 … 2^30  |   64 |
| `cuda`      | cuda  | –             | 2^28               |    1 |
| `cuda full` | cuda  | –             | 2^16, 2^18 … 2^30  |    8 |

All runs use double precision and 100 iterations.

## Artifacts

```
babelstream-<jube id>/
  summary.md          tables per model, best average triad, failures, plots
  results.json        context and every record in one document
  results.csv         one row per run and kernel
  context.json        git commit, system, tool versions
  records/<key>.json  one record per job
  raw/<key>/          job script and output, lscpu, Spack lock if any
  plots/              bandwidth against threads or array size, SVG and PNG
```

The record format and the bandwidth definitions are described in
`../babelbench/readme.md`. The headline metric is the average triad bandwidth.

A job that exits non-zero is marked as an error by JUBE's platform and never
reaches post-processing; `jube status` shows it. A job that finishes but
prints no results, or reports a validation failure on stderr, still gets a
record, is listed under failures in the summary, and marks its postprocess
workpackage as an error. BabelStream does not change its exit status on
validation failures, so that case is checked explicitly.

The postprocess step passes babelbench everything it records: the run's
parameters from JUBE, the node and job id from the job's directory, and the
job script and output as files to keep.

## Design notes

**Spack build.** With `--tag spack`, BabelStream is built from Spack's
builtin recipe with nothing but the model and, for CUDA, the platform's
`cuda_arch`. The recipe's defaults include BabelStream's own
`-O3 -march=native`, which targets the CPU of the node Spack builds on, so
build on a node of the same CPU type as the one you measure.

**Pinning.** Every job gets the whole node, and the single task is started
with all CPUs of the node and `--cpu-bind=none`. OpenMP then places threads
with `OMP_PLACES=cores` and `OMP_PROC_BIND=spread`. Giving the task only as
many CPUs as threads would pin a small run to one corner of one socket.
