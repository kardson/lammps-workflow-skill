# Version-bound knowledge routing

Keep source catalogs and downloaded manuals outside the installed skill. Each entry identifies topics, engine profile IDs, exact release/commit, source URL, local path and any observed file identity. `tools/reference_catalog.py` selects by explicit engine ID and topic; no result is a gap, not permission to fall back to a different release.

Use the selected manual's directory with tools/search_manual.py. Distinguish official command syntax, interface-specific documentation, tutorial engineering examples and research-method evidence. NEP CPU and MatPL GPU documentation describe different pair interfaces. Software-source catalog acquisition status is historical and does not establish current runtime readiness.

Selected RST pages are useful offline references but do not supply a complete rendered manual or all cross-reference targets. Preserve these limits in the catalog. A file hash checks a specific local copy; it does not establish model validity or scientific acceptance. No server is required.
