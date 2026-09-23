<!--
  ============================================================================
  SPDX-FileCopyrightText: ADAC Contributors
  SPDX-License-Identifier: Apache-2.0
  ============================================================================
-->

# Application Benchmarking Effort

Benchmarking applications across machines and benchmarking harnesses, with
one description of each benchmark that every harness can run.

## Contact

Jayesh Badwaik [email](mailto:j.badwaik@fz-juelich.de). I lead this effort; ask me for access to the
working document, to machines, or to anything else referred to here.

## Status

One row per application, model, harness and machine; one column per way of
building it. A new machine, harness or build is a new row or column.

| Application | Model  | Harness | Machine   | From source | Spack    |
| ----------- | ------ | ------- | --------- | ----------- | -------- |
| BabelStream | OpenMP | JUBE    | JURECA-DC | runs        | untested |
| BabelStream | CUDA   | JUBE    | JURECA-DC | untested    | untested |

- **runs**: built, ran and post-processed end to end on the machine.
- **untested**: written, not yet run on the machine.

Next steps are issues in the tracker, not text here.

## Layout

One directory per application. Inside it, one directory per harness,
shared build recipes, and the post-processing. Each has its own readme on
how to run it.
