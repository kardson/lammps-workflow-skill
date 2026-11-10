# Decisions, assumptions and scoped blockers

Use templates/decision-log.json beside the actual plan when decisions need a history. The plan remains the authority for current scientific values; the log records their origin and reasoning, not a competing parameter set.

Each entry has a stable id, kind (DECISION, ASSUMPTION, QUESTION or ISSUE), summary, status, source and related_fields. Use status OPEN, INVESTIGATING, FIX_PROPOSED, RESOLVED or SUPERSEDED. `blocks` lists exact affected stage identifiers; an empty list blocks nothing. Include release_condition for unresolved blockers. Sources reference actual user decisions, literature, evidence or an explicitly labeled assumption; do not invent confirmation.

A resolved decision records resolution and evidence. A repaired issue additionally records selected_fix, verification and regression_scope; retain the original failure. Assumptions remain distinguishable from confirmed decisions after resolution. Existing authorization is linked and reused; issue status never creates new execution permission.

Suggested stage names are environment, local_tools, research_structure, research_input, launch, analysis and scientific_acceptance. A missing orientation may block research_structure and research_input, while environment and local_tools proceed. Failed or partial data may still support a diagnostic report. `tools/decision_records.py` only selects explicitly listed unresolved blockers; an empty result is not proof that the stage is scientifically ready or authorized.
