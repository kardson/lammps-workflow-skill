# Scoped compatibility evidence

`tools/validate_compatibility.py --evidence FILE --model-sha256 HASH --engine-id ID --scenario SCENARIO` queries v1 records described by schemas/compatibility-evidence.schema.json. Evidence paths resolve beside the evidence index. It reads local files only; no inference or host calls.

Exact model identity, engine profile and scenario must match. Installation, numerical, MPI, deposition, restart and physical_accuracy dimensions stay separate. PASSED_RECORDED means a matching recorded validation with available source references; it does not authenticate raw numerical adequacy or certify broader physics. FAILED and PASSED records coexist as CONFLICTING rather than silently replacing each other. Missing source files make effective status UNVERIFIED while recorded_status is retained.

Exit 0 means query completed, including an all-unverified answer; 1 means a matching failed/conflicting dimension; 2 means malformed evidence, missing input or usage error. Never interpret exit 0 alone as compatibility approval. Historical evidence must retain actual checks, thresholds and limits; a repaired engine requires its own evidence or explicitly justified unchanged-path linkage.
