# Capability map

All bundled tools support `--help`. Resolve them from the skill root, using the selected Python interpreter. They do not execute an MD input, run MD, launch SSH, train potentials, or create monitoring jobs.

| Request | Entry point | What it establishes |
|---|---|---|
| Create an independent research workspace | `tools/init_workspace.py --workspace ABSOLUTE_PATH` | Project directories, draft plan and project route, preserving existing files |
| Observe local or compute-host environment | `tools/check_environment.py --role controller --output NEW_JSON` | Dated local observation; optional `--lmp EXACT_BINARY` calls only `-h` |
| Require features from selected binary | Add `--package NAME --pair-style NAME --fix-style NAME` as needed | Exact membership in help sections, not numerical support or plugin loadability in a production input |
| Register potential file | `tools/inspect_potential.py FILE --kind nep --require-element SYMBOL --output NEW_JSON` | File size/hash, NEP header and element coverage, not suitability |
| Register empirical potential | Same command with `--kind empirical` | Exact file identity; no speculative format parsing or mixing-rule validation |
| Search a matching offline manual | `tools/search_manual.py --manual-dir DOC_SRC --query 'fix deposit' --limit 10` | Literal matches with source lines; no online retrieval or service |
| Index one input and compare four literal plan fields | `tools/inspect_input.py --input FILE --plan PLAN --output NEW_JSON` | Scoped text review; variables/includes/control flow are not executed |
| Summarize segmented single-line thermo logs | `tools/parse_log.py --log FILE --output NEW_JSON` | Errors, warnings, block statistics and partial coverage; no job-state or scientific acceptance |
| Build bulk/slab/stacked interface candidates | `tools/prepare_structure.py --config CONFIG --output-directory NEW` | Explicit unrelaxed geometry, mapping and source identity; no automatic scientific choices |
| Audit structural geometry/type mapping | `tools/audit_structure.py --help` | Finite geometry, declared bounds and user-threshold close pairs |
| Prepare fresh atomic-beam input packages | `tools/prepare_input_package.py --help` | Literal parameterized inputs and inventory; no engine/numerical acceptance |
| Stream trajectory counts/composition/geometry | `tools/analyze_trajectory.py --help` | Explicit window/grid metrics from supported text dumps, with partial/failure states |
| Check species balance and counter-derived rates | `tools/analyze_balance.py --help` | Explicit initial/snapshot/cumulative inserted/removed counts and supplied area/time; no invented counters |
| Summarize independent replica-level scalars | `tools/summarize_replicas.py --help` | Conditional mean/SD/SEM/intervals; no proof of independence |
| Software preview and diagnostic delivery | `tools/render_structure.py --help`, `tools/generate_report.py --help` | Annotated PNG, standalone HTML, explicit scientific limits |
| Prepare bounded candidates and local input archive | `tools/prepare_sweep.py --help`, `tools/bundle_package.py --help` | Proposed variants, byte-checked ZIP, zero submissions/transfers |
| Exercise the local pipeline on artificial fixtures | `tools/demo_local_pipeline.py --output-directory NEW` | Geometry/I/O/report/render behavior only; no MD or force inference |
| Propose scientific plan | `templates/plan.json`, [deposition](deposition.md) | Explicit unknowns and agreed criteria; no scientific defaults |
| Track run/restart evidence | `templates/attempt.json`, [records](records.md) | A record format; no submitted job or execution authorization |

Every JSON report uses a new destination and refuses to overwrite existing evidence. A complete environment receipt is not a numerical test. Detailed limits, supported formats and exit codes for the local helpers are in [local-first workflow](local-first.md). The input/log tools support scoped diagnostics, not a general LAMMPS interpreter or a full preparation/scientific audit. Record unsupported constructs rather than claiming exhaustive inspection.

The structure/analysis/render helpers have optional scientific-library dependencies. Read [local toolchain contracts](local-toolchain.md) before selecting configurations or interpreting results; the original six helpers remain standard-library based.
