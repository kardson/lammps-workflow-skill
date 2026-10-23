# Local preparation and analysis, compute-host execution

Default to the controller for research planning, literature/manual lookup, potential registration, structural preparation, static input review, result parsing, plots, visualization, reports and project history. This makes interactive work independent of host availability. It is a division of responsibilities, not a demonstrated performance ranking.

| Operation | Default location | Evidence still needed elsewhere |
|---|---|---|
| Plans, structures, potential cards, version-matched documentation | Controller | Researcher decisions and original sources |
| Text/data conversion, static input review, small log summaries | Controller | Actual engine syntax/runtime and numerical tests |
| Analysis, figures and interactive visualization | Controller | Analysis method, selection/units and source provenance |
| Retrieve outputs | Select only needed files/frames | Host source identity, completion/missing-output evidence |
| LAMMPS/interface build | Target host or matched build environment | Target ABI, MPI/runtime, dynamic linking and architecture compatibility |
| Compute-host availability, processes and resource state | Compute host | A dated local copy cannot establish live state |
| Model inference, short MD, CPU/GPU comparisons, insertion/restart validation, production and benchmarks | Authorized compute backend | Explicit permission and numerical/scientific acceptance |

Installation can be prepared locally by downloading exact sources, dependencies and recipes. A native Windows binary is not a WSL/Linux binary. A matched local Linux build may be transferable, but compiler/ABI, MPI, library paths, CPU/GPU architecture and the target runtime still require verification. Keep existing workloads isolated.

For large trajectories, avoid an unconditional full transfer. Estimate size and local memory/disk, then select required files/frames or use streaming/chunked analysis. Source-side extraction may be more practical than moving every byte, but is a separately scoped host operation. Keep the original data and frame/ID/unit mapping; do not silently drop required evidence. GPU-intensive analysis also depends on actual local hardware and library support.

## Local tools

### Static input index

```text
python SKILL_ROOT/tools/inspect_input.py --input RESEARCH_ROOT/inputs/in.case --plan RESEARCH_ROOT/01_plan/md-plan.json --output RESEARCH_ROOT/records/input-review.json
```

Reads a single UTF-8 input as text. Supports ordinary quoted tokens, comments and `&` continuation. Records selected commands and compares only literal `units`, `atom_style`, `boundary` and `timestep` with the optional plan. It does not follow includes, evaluate variables/control flow or call Python/shell/LAMMPS. Triple-quoted blocks stop indexing; parse issues and unresolved branches remain partial. Repeated/missing/dynamic assignments are unverified, not silently resolved with defaults.

`MATCH` means the selected literal field matches a draft/plan field. It is not scientific confirmation, a full preparation audit, engine validation, potential mapping or execution permission. Type-to-element mapping, structure and overlaps, interface syntax and all scientific choices still require their own review. Exit 1 indicates a literal mismatch; exit 0 only means a report was written without that mismatch.

### Segmented log summary

```text
python SKILL_ROOT/tools/parse_log.py --log RESEARCH_ROOT/results/log.lammps --output RESEARCH_ROOT/records/log-summary.json
```

Streams conventional single-line thermo tables containing a `Step` or `Time` column, retaining separate headers/blocks including step resets. Reports first/last, finite min/max, counts, warning/error evidence and nonfinite/malformed rows. Does not store the full table in memory. It records a digest of the observed byte stream and whether size/mtime changed during reading; an actively changing log needs another explicitly requested snapshot before using it as final evidence.

YAML/multi-line thermo is reported unsupported. Tables without a `Step` or `Time` header, arbitrary column-label formatting, partition-interleaved logs and trajectory observables require another parser. Warnings are retained, not treated as automatic physical failure. Nonfinite values become null with explicit counts; they are never silently discarded as valid data.

Exit 1 means errors/nonfinite values/malformed rows or a changing source were observed; exit 2 means unsupported/no supported thermo. Exit 0 means a scoped summary was written; it does not prove job completion, numerical stability, equilibrium or scientific validity. A `Loop time` line closes only its associated segment. Later errors remain visible. Time/units and production windows are not guessed, and statistical uncertainty/atom balance require separate analysis.

Both tools preserve source files, refuse to overwrite reports, and write outside the installed skill. Their fixtures are software tests, not research calculations. Use the matching [LAMMPS parsing rules](https://docs.lammps.org/Commands_parse.html), [run output](https://docs.lammps.org/Run_output.html) and [thermo documentation](https://docs.lammps.org/thermo_style.html) for actual input/output interpretation.
