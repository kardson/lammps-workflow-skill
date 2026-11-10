# Bounded validation cases

`schemas/validation-case.schema.json` defines case identity, provenance, execution category, exact combination, preconditions, resources, input identities, checks and expected outputs. A case definition is not execution permission. Null combination/resources remain unbound, not defaults.

Installation, inference, MD, performance, scientific evaluation and local logic are separate categories. Engine help is installation evidence; a finite artificial fixture is local software evidence. Historical engine receipts must retain their date and exact tested scope. Thresholds need a source and units fixed before execution.

`tools/run_validation.py --operation plan --case CASE.json --category local_logic` lists selected cases without execution. Omitting category selects none. Repeat --case or --category for additional cases/categories. This is not execution authorization.

`tools/run_validation.py --operation parse --case CASE.json --result-directory DIRECTORY` parses one existing result. Currently only `termination_v1` and its exit_code metric are supported. Missing required outputs, corrupt/inconsistent terminal evidence and unknown metrics cannot pass. Exit 0 means the declared supported checks passed; 1 means partial/failed/unverified; 2 means invalid input/dependency/usage. No process is launched, even for an engine-category definition.

The additional `lammps_single_line_v1` parser reuses the streaming log reader on `log.lammps`, together with a terminal receipt. Supported metrics are exit_code, error_count, nonfinite_values, thermo_block_count, last_step and last_block_completed (0/1). Last step belongs to the final thermo block; reset blocks are not combined. A missing final loop marker, unsupported/corrupt thermo, errors or nonfinite values prevent a pass even if omitted from requested checks. Exact target steps and tolerances must be declared by the case. Input identities are checked for both parsers. Historical exits in other formats need a traceable adapter; do not invent terminal records in raw directories.

`historical_record_v1` selects one object through historical_source {path,pointer,observed_date}. The source must be in inputs with its digest. It compares explicitly declared scalar fields/thresholds, preserves HISTORICAL_NOT_RERUN, and never creates terminal records. Sources are limited to 16 MiB. This checks preserved receipt fields, not raw energy/force recomputation. Corrupt pointers, changed identities, missing fields and failed checks cannot pass. Historical definitions must not be submitted as executable requests.

Private deployments may supply an explicit execution adapter; no engine execution is bundled in this public CLI. Further raw numerical comparison parsers remain pending. Selecting all categories must never implicitly authorize them. Missing outputs, failed predictions and unsupported parsers must remain visible rather than becoming zero-valued metrics or passes. The synthetic receipt example proves software parsing only.

For a deliberately negative terminal test, explicitly set
`expected_terminal_state: "FAILED"` and declare exactly one `exit_code` check with
`operator: "eq"` and an integer nonzero `value`, with the usual unit/source.
Without this field, expected process termination remains `SUCCEEDED`. The report
retains `process_terminal_state` and `expected_terminal_state` separately from
the validation `status`. An expected nonzero exit can pass the declared check;
a different exit, missing required output or inconsistent receipt cannot.
This option applies only to terminal parsers. It does not prove a clean KOKKOS
shutdown, the intended diagnostic message or absence of parser errors; those
need explicit supported evidence checks or separate inspection. Existing historical
case results are not rewritten or reclassified by this declaration.
