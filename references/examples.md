# Examples by evidence level

Resolve scripts from the installed skill root and select a Python interpreter with
the dependencies below. Use new output paths. Parameters in fixtures are artificial
and must not populate a research plan. No command in the first two levels executes
LAMMPS or infers forces.

| Level | Inputs and executable example | Dependencies | Outputs and limits |
|---|---|---|---|
| Artificial parser fixture | `python tools/run_validation.py --operation plan --case validation/cases/local-receipt-fixture.json --category local_logic` | Python and jsonschema | Lists a synthetic receipt case; no actual receipt generated or engine run |
| Artificial statistics fixtures | `python tests/test_replica_evidence.py`; `python tests/test_block_statistics.py` | Python, SciPy for conditional intervals | Temporary scalar/time-series sources and assertions; independent scientific runs are not established |
| Artificial report fixture | `python tests/test_conclusion_evidence.py` | NumPy, Matplotlib | Temporary HTML/PNG/native indices, changed-file and missing-evidence checks; no physical result |
| Local engineering demonstration | `python tools/demo_local_pipeline.py --output-directory ABSOLUTE_NEW_DIRECTORY` | ASE, NumPy, SciPy, pandas, Matplotlib, OVITO/PySide6, spglib, JupyterLab (the demonstration records these versions) | Artificial bulk/slab/interface, candidate inputs, input review, ZIP, trajectory metrics, counters, replica summary, previews and report; no attempt or remote submission |
| Real engine engineering evidence | [Reference deployment](validated-deployment.md), [case protocol](validation-cases.md) | Exact external engine/interface/model/runtime and separately authorized execution | Dated bounded LJ/NEP checks, with raw files retained privately; public skill does not supply executable site bindings or model weights |
| Scientific research example | Not yet available as accepted CdTe/GaAs evidence | Accepted structures, suitable potential, scientific plan, comparable reference labels and run permission | No accepted growth or reference-accuracy result is claimed; engineering thresholds and fictitious parameters cannot substitute |

Run CLI examples from the skill directory or replace every relative source path
with its absolute path. Unit-test scripts resolve their resources internally and
can be invoked from another working directory. They write temporary fixtures,
not a permanent result deliverable. The local demonstration writes persistent
outputs and refuses an existing destination; it may need a working offscreen
OVITO rendering environment. It does not open the researcher's desktop applications.

## Trace an actual engineering result

An external engineering example is reproducible only with its original case,
exact inputs/model/binary identities, predeclared thresholds, resource scope,
attempt/terminal evidence and retained numeric outputs. The public deployment
summary is a description of observations, not the raw replay package. A site can
construct a new case using `schemas/validation-case.schema.json` and explicitly
select planning or existing-output parsing through `run_validation.py`; execution
belongs to its private adapter and current authorization.

## Extend the local demonstration

For stage observations, use [stage contracts](stage-contracts.md); for supplied
event histories use [deposition metrics](deposition-metrics.md). For existing static
LAMMPS output imports and reference metrics use [reference evaluation](reference-evaluation.md).
These routes expose partial/failed samples rather than discarding them. Their
method pages and regression fixtures define supported formats and unresolved
evidence. A report can show partial outputs, but must retain original tables,
algorithm/configuration identities and limits alongside plots.
