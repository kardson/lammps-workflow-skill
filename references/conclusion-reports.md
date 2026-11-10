# Conclusion evidence in local reports

`generate_report.py` keeps its existing geometry diagnostic route. Optional
`--evidence-config path/to/conclusions.json` adds a declared conclusion index.
Paths within that configuration resolve against its containing directory.

The JSON object contains `report_class` (`diagnostic`, `engineering` or `research`)
and a `claims` list. Each claim has a unique `id`, `statement`, `attempt`,
`method_version`, `time_window`, `atom_selection`, `formula`, `unit`, `result`,
`uncertainty`, `acceptance_conditions`, `limitations`, and `sources`.
Each source specifies `path`, expected `sha256`, and an explicit `locator`
(JSON pointer, CSV row/column selection, or original file lines).
Use null for unresolved metadata; do not manufacture a time window or interval.

The index observes actual source identities and exposes missing metadata,
unavailable files, and changed or unspecified hashes. It does not interpret
locators or recompute declared results. `DECLARED_CHAINS_PRESENT` means that
metadata and file identities are present, not that the conclusion is correct.
Scientific acceptance always remains `UNVERIFIED`. Report class is descriptive;
choosing `research` cannot promote an engineering fixture into research evidence.

Outputs retain HTML and PNG and add native `conclusion-index.json` and
`report-configuration.json`. The latter records tool/source identities and plotting
configuration. Keep the original analysis CSV/JSON and all linked raw evidence;
the image is a display sample and does not replace numeric artifacts. For transfer,
bundle the actual linked files separately and verify their identities. Local
absolute paths in private reports are not portable links or suitable public data.

Partial analysis and incomplete claims may be reported with their explicit status.
With no evidence configuration the report remains diagnostic with an empty,
partial conclusion index. CLI exit zero means report creation, never acceptance.
