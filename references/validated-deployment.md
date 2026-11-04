# Reference deployment and engineering validation

Status as of 2026-11-04, skill v0.4.0. This is a sanitized integration summary from a separately maintained reference deployment, not a binary distribution or a claim that the reader's machine is configured. Private host identities, paths, raw outputs and research decisions are excluded.

## Observed combination

| Component | Reference deployment |
|---|---|
| Host/runtime | Linux under WSL2; Windows controller for preparation and delivery |
| CPU engine | LAMMPS 30Sep2026 with NEP_CPU, MANYBODY and OPENMP |
| GPU engine | LAMMPS stable_22Jul2025_update4, commit `611ca3b7f8525ba802373b04f9e3d632d515f7e3`, with MatPL NEP KOKKOS |
| GPU toolchain | CUDA 12.8.1, GCC 13.3, OpenMPI 5.0.10; Blackwell120/sm_120; double-precision NEP |
| Model | Intact NEP89 `nep89_20250409.txt`; no header/weight truncation |
| Integration source identity | Archived MatPL snapshot SHA-256 `f58659b92592743848aff53e5f353b4dee0e11cd78ddb9d0ca61310228d8aaf4`; archive and local patch kept in the private deployment |

The MatPL snapshot did not compile unchanged against the reference LAMMPS 2026 KOKKOS types. The independently installed GPU engine uses the upstream-listed 2025 update4 release. Do not generalize this observation to all MatPL revisions or replace another installation without checking its provenance. CPU and GPU versions differ; binary restarts were tested only within the same engine.

## Completed checks and actual limits

| Check | Observed scope |
|---|---|
| Installation | Exact executable help, required packages/styles, linked libraries and runtime entry paths passed |
| Official LAMMPS examples | Release-matched unmodified LJ melt (250 steps) and atomic deposition (10000 steps), on CPU and GPU KOKKOS, completed normally |
| NEP89 inference | CPU/GPU energy and force comparison passed predeclared engineering tolerances on one artificial four-element fixture |
| MPI | One versus two CPU ranks; one versus two GPU ranks sharing one physical GPU; agreement passed |
| Energy/force relation | Central finite difference of one atom's x component passed; not exhaustive force/virial verification |
| Normal restart | Short NVE continuous versus same-engine split/resume passed, with model/pair and fix definitions explicitly restored |
| Open surface/insertion | Periodic x/y, nonperiodic z, changing atom count and actual motion of inserted atoms passed |
| Deposition restart | Restart before a later insertion, then resume and insert more atoms; final snapshot matched continuous run |
| Negative file handling | Local GPU entry guard: nine one/two-rank file-error cases, including only one rank failing, rejected without the original KOKKOS finalize diagnostic |
| Repair regression | Five valid inference/MPI/deposition/restart runs matched the previous engine within the declared numerical tolerance |
| Controller software | Local structures/input packages, text diagnostics, geometry/composition/balance, replica statistics, software rendering and HTML/PNG delivery checked; actual notebook kernel and authenticated Jupyter HTTP/API checked |

These checks establish bounded engineering functionality. Long-duration stability, larger scale/more ranks, multiple GPUs, complete virial checks, cross-engine restart compatibility, potential physical applicability and performance remain outside this evidence. Desktop/browser interaction remains researcher-managed. Neither fitting/training nor production scientific acceptance is included.

## Model preflight and the file-exit repair

Use `tools/preflight_nep_model.py` with explicit `--model`, `--expected-sha256` and `--elements`. It rejects a changed file identity or missing required species before an authorized launch. JSON is printed to stdout; it does not launch LAMMPS or validate complete model syntax. The expected digest must come from the selected model record, not be recalculated from an unknown file merely to make a check pass.

In the tested MatPL snapshot, failure to open a model calls `exit(1)` inside the reader and bypasses normal KOKKOS cleanup. The reference repair checks regular-file/readability/nonempty state on every rank before reading, reduces failures collectively, and sends all ranks through LAMMPS `error->all`. It is an external deployment patch, not bundled here or assumed present on other hosts. It does not overhaul malformed-model parser exits or eliminate file-replacement races; keep selected files unchanged during launch. A preflight helper alone does not repair an unpatched binary's error path.

When authorized to validate another deployment, preserve exact inputs/model identity, declare numerical thresholds before execution, retain failed evidence, and verify terminal logs, actual styles, atom counts and new-atom trajectories. Adapt to its installed interfaces rather than treating this reference combination as a universal installation requirement.
