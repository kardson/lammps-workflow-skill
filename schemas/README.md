# Record schemas

These v1 structural schemas accept existing draft templates, including unresolved nulls. Additional fields remain allowed for existing private extensions. They validate required sections, record identity, lifecycle status names and selected numeric/file identity constraints. Flexible scientific values may be strings, objects, arrays or null until their representations are standardized; passing is not scientific readiness.

Validation and its tests require the optional `jsonschema` Python package. Existing preparation and inspection tools do not import this dependency. No migration is needed for unchanged v1 templates. Unknown versions are rejected rather than silently migrated.

Run the focused tests from the skill root with `python -m unittest discover -s tests -p test_record_schemas.py`. Tests include an actual locally generated artificial candidate package, with no force evaluation. The package schema matches the current generator, which does not emit record_type or schema_version; select it explicitly.

Use `python SKILL_ROOT/tools/validate_case.py --record RECORD` for plan/model/attempt, or add `--kind package-manifest` for a generated package manifest. Output is JSON on stdout; exit 0 means structurally valid, 1 invalid, 2 input/dependency error. No file is written. Install the optional dependency using requirements-validation.txt in the selected analysis environment.

Add `--check-links` to check explicit local references, model identity/type coverage and package inventories. References resolve beside the record unless `--reference-root` is explicit. Optional `plan_binding` on an attempt contains `file`, expected `sha256`, plan `id` and `schema_version`; changed bytes or mismatched identifiers are reported. Exit 0 with a PARTIAL links report still means unresolved checks, not complete acceptance. Engine compatibility and restart semantics remain unimplemented. No LAMMPS input is interpreted or executed.

An attempt can include `model_card` for identity/interface comparison and `input_declarations` for comparison with the bound plan's units, atom_style, boundary, type_to_element and timestep. These are declared values, not an audit of actual script behavior. A parent restart identity is checked as a file; its runtime compatibility still requires evidence. Missing declarations remain unknown.

Optional `compatibility_evidence` references a JSON record with executable, interface_revision, precision, potential_sha256, scenario, status and raw_evidence (paths relative to that evidence record). Compare against the attempt's validation_scenario. The checker rejects mismatched identities/scenarios and missing raw files. A PASSED label and existing files do not establish that the underlying numerical test is adequate; raw contents and thresholds still require domain assessment. This is evidence linkage, not a runtime compatibility certification.
