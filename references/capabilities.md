# Capability map

Machine-readable task/tool metadata is in [capabilities.json](../capabilities.json), linked to the source-reviewed [CLI contracts](cli-contracts.md). It describes implemented bundled helpers, not remote execution adapters. Registry tests detect mismatched entries and duplicated contract facts.
For version-matched manuals and interface sources, use [knowledge routing](versioned-knowledge.md).
For runnable local examples and the distinction from external engine or research evidence, see [examples by evidence level](examples.md).

All bundled tools support `--help`. Resolve them from the skill root, using the selected Python interpreter. They do not execute an MD input, run MD, launch SSH, train potentials, or create monitoring jobs.

| Request | Entry point | What it establishes |
|---|---|---|
| Create an independent research workspace | `tools/init_workspace.py --workspace ABSOLUTE_PATH` | Project directories, draft plan and project route, preserving existing files |
| Observe local or compute-host environment | `tools/check_environment.py --role controller --output NEW_JSON` | Dated local observation; optional `--lmp EXACT_BINARY` calls only `-h` |
| Require features from selected binary | Add `--package NAME --pair-style NAME --fix-style NAME` as needed | Exact membership in help sections, not numerical support or plugin loadability in a production input |
| Register potential file | `tools/inspect_potential.py FILE --kind nep --require-element SYMBOL --output NEW_JSON` | File size/hash, NEP header and element coverage, not suitability |
| Check selected NEP before launch | `tools/preflight_nep_model.py --model FILE --expected-sha256 DIGEST --elements SYMBOL ...` | Reject changed identity or absent species; stdout JSON, no inference or automatic launch |
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
| Validate linked plans, audits and attempt records | `tools/validate_case.py --help` | Schema/reference checks; not scientific approval or a live host query |
| Compare runtime/model compatibility | `tools/validate_compatibility.py --help` | Explicit registry facts and unresolved evidence; no inferred interaction physics |
| Prepare and parse engineering validation cases | `tools/run_validation.py --help` | Case plans or existing-output checks, no engine launch |
| Prepare static prediction inputs | `tools/prepare_static_prediction.py --help` | Explicit run-0 candidate package with identities; no model inference |
| Import existing static energy/force outputs | `tools/import_predictions.py --help` | Geometry/atom mapping and terminal evidence checks; failed samples retained |
| Evaluate comparable reference labels | `tools/evaluate_reference.py --help` | Energy/force/stress metrics and coverage, without fitted energy offsets or acceptance |
| Audit declared stages and observations | `tools/inspect_stages.py --help` | Contract/link/condition checks, without equilibrium certification or process control |
| Classify supplied deposition events/cohorts | `tools/analyze_events.py --help` | Disk-backed event accounting; no automatic trajectory event detection |
| Summarize explicitly selected time blocks | `tools/summarize_time_series.py --help` | Conditional block intervals with diagnostics, no frame-IID assumption |

Additional source-reviewed helpers are listed in the machine-readable registry;
consult their `--help` and linked method page for exact arguments. Replica summaries
can bind per-run scalar sources, seeds and windows; incomplete research evidence
withholds intervals. `prepare_sweep.py --plan-only` writes bounded nonexecutable
proposals while scientific values remain unresolved. `generate_report.py
--evidence-config` adds a partial/declared conclusion index and native reproduction
configuration, always with scientific acceptance unverified.

Reports written to files use a new destination and refuse to overwrite existing evidence; the model preflight prints JSON only to stdout. A complete environment receipt is not a numerical test. Detailed limits, supported formats and exit codes for the local helpers are in [local-first workflow](local-first.md). The input/log tools support scoped diagnostics, not a general LAMMPS interpreter or a full preparation/scientific audit. Record unsupported constructs rather than claiming exhaustive inspection.

The structure/analysis/render helpers have optional scientific-library dependencies. Read [local toolchain contracts](local-toolchain.md) before selecting configurations or interpreting results; the original six helpers remain standard-library based.

## External reference deployment, now exercised

CPU/GPU installations and bounded inference/MPI/open-boundary/insertion/same-engine restart checks have passed in a separate reference deployment. The model-file GPU exit defect was repaired there and regression-tested. See [validated combination and exact scope](validated-deployment.md). These are agent-guided capabilities with actual external execution evidence; they are not new bundled job submission or build adapters. The public tool installation remains portable and contains no working host configuration, binaries, patch deployment, weights or raw research outputs.
