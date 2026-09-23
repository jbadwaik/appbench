# BabelStream

- system: jurecadc
- captured: 2026-09-23T12:49:10+00:00
- repository: `18582e4ef374f1252b01e50c9696d47eb5ded22c` (dirty)

1 runs, 0 failed. Bandwidths in GB/s (10^9 bytes); average over iterations 2..n, best in brackets.

## omp

| threads | 2^e | Copy | Mul | Add | Triad | Dot | node |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 128 | 28 | 218.3 (219.2) | 206.4 (207.4) | 227.8 (228.5) | 230.1 (231.3) | 307.6 (309.7) | jrc0189 |

Best average Triad: **230.1 GB/s** with 128 threads at 2^28 elements.
