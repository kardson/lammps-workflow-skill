# Record compatibility and interpretation

Read this for record validation, interchange or non-destructive upgrades. Current schemas describe v1 plans, model cards and execution attempts. The current generated candidate manifest is a separate unversioned format selected explicitly. Existing v1 records need no rewrite. Unknown versions require an explicit future migration; never change a version number to make a record pass.

`tools/record_io.py` reads UTF-8 (including BOM), requires an object and rejects unsupported explicit versions. Its `copy_record` preserves original bytes, null decisions and extension fields, and refuses to replace an existing destination. This copies a supported record; it does not upgrade a version or establish schema validity. Run structural validation separately.

References resolve beside their containing record. A legacy project-root reference may use the validator's explicit `--reference-root`; do not guess between directories. References inside a compatibility-evidence record resolve beside that evidence file. Absolute paths remain usable in private records but are not portable public examples. Package members must remain inside the package directory.

New observations use ISO 8601 timestamps with an explicit UTC offset (prefer UTC). Preserve historical timestamps verbatim; a timestamp without timezone remains ambiguous, not silently converted. Observation time is not launch time or simulation time.

Retain declared unit systems and units on derived metrics. LAMMPS timestep/temperature values refer to the plan's declared units; unit conversion requires an explicit adapter and provenance. A missing unit is unknown, not automatically metal units. Do not convert scientific values during record copying.

Preserve states as recorded. Preparation, authorization, execution, observation, collection, numerical validation and scientific acceptance describe separate facts. Missing or stale observations do not imply job failure or justify relaunch. Null confirmation stays unresolved. A structural validation pass or matching declaration does not promote a state to accepted.

See [schema usage and limits](../schemas/README.md) for current CLI behavior and [execution records](records.md) for research evidence requirements.
