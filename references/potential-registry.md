# Potential discovery records

Use templates/potential-index.json and schemas/potential-index.schema.json to index existing empirical and pretrained ML potentials. Keep real model cards, weights and identities in the private workspace. The artificial two-kind fixture in tests is software data, not a semiconductor recommendation.

Each entry retains source repository/revision, license and citation, file identity, elements, units, applicability, metrics and scientific status. Unknown source or unit fields remain null with missing evidence recorded; no mixing rule, unit system or target suitability is inferred. Indexing does not read the weight file or certify current availability.

`tools/potential_registry.py` provides read-only search by elements and kind. Energy-MAE threshold filtering requires an explicit dataset and scenario, matching metric context and an evidence reference. Missing metrics/context cannot qualify. Results are candidates; the caller must inspect raw evidence, coverage, energy conventions and target-domain relevance. A matching number is not scientific acceptance. Training is excluded.

Use `load_index(path)` to validate a file against the index schema and reject duplicate IDs before querying; it requires the optional jsonschema dependency. `search(entries, ...)` operates on already loaded entries and does not write, download, train or evaluate potentials. Paths in real entries are relative to the index file, unless explicitly absolute. Preserve unknown license/citation information and record the gap; software licensing is not automatically a license for model weights.
