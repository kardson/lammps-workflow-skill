# Candidates and restart preparation

Keep candidate variants associated with the base configuration/plan and explicit proposed changes. Record why a scientific parameter changes; a generated candidate does not confirm that change or submit a job. Existing sweep manifests preserve requested variants, prepared variants and failures separately.
Research-purpose sweeps require a nonempty reason per variant and a plan_file in the base configuration. Engineering fixtures remain explicit software examples. Prepared variant records retain the reason and captured research bindings.

Use templates/restart-candidate.json to propose a continuation. Record the actual parent attempt, immutable checkpoint identity, source/target engine profiles, potential identity, completed and target steps, stage, fix-state evidence and counter origin. Compatibility evidence paths resolve beside the candidate. `tools/restart_candidate.py` checks local file identity and declarations only; binary contents, random/fix state restoration and numerical compatibility require actual supported-engine evidence.

DECLARATIONS_COMPLETE is preparation metadata, not runtime approval. Cross-engine binary restart remains incomplete without a separate supported adapter/validation; this helper never renders a general recovery script or launches a run. A later authorized continuation receives a new attempt, preserving its parent and checkpoint. Keep original files and failed candidates.
