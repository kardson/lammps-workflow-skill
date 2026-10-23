# Capability map

All bundled tools support `--help`. Resolve them from the skill root, using the selected Python interpreter. They do not load an MD input, run MD, launch SSH, train potentials, or create monitoring jobs.

| Request | Entry point | What it establishes |
|---|---|---|
| Create an independent research workspace | `tools/init_workspace.py --workspace ABSOLUTE_PATH` | Project directories, draft plan and project route, preserving existing files |
| Observe local or compute-host environment | `tools/check_environment.py --role controller --output NEW_JSON` | Dated local observation; optional `--lmp EXACT_BINARY` calls only `-h` |
| Require features from selected binary | Add `--package NAME --pair-style NAME --fix-style NAME` as needed | Exact membership in help sections, not numerical support or plugin loadability in a production input |
| Register potential file | `tools/inspect_potential.py FILE --kind nep --require-element SYMBOL --output NEW_JSON` | File size/hash, NEP header and element coverage, not suitability |
| Register empirical potential | Same command with `--kind empirical` | Exact file identity; no speculative format parsing or mixing-rule validation |
| Search a matching offline manual | `tools/search_manual.py --manual-dir DOC_SRC --query 'fix deposit' --limit 10` | Literal matches with source lines; no online retrieval or service |
| Propose scientific plan | `templates/plan.json`, [deposition](deposition.md) | Explicit unknowns and agreed criteria; no scientific defaults |
| Track run/restart evidence | `templates/attempt.json`, [records](records.md) | A record format; no submitted job or execution authorization |

Every JSON report uses a new destination and refuses to overwrite existing evidence. A complete environment receipt is not a numerical test. Agent-guided input inspection and analysis are procedures, not a general LAMMPS parser or an automatic validator. Record unsupported input constructs rather than claiming exhaustive inspection.
