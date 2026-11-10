# Deposition observables and evidence boundaries

Use [the local toolchain guide](local-toolchain.md) for the base command/configuration interfaces. The definitions and extensions below do not authorize running a simulation.

| Quantity | Supported definition / required evidence | Cannot infer from it |
|---|---|---|
| Snapshot species count | All mapped atoms in a complete frame | Number of incident atoms retained or successful insertions |
| Appeared/disappeared IDs | Difference between selected snapshots | Attempts, reflections, escape causes or cumulative flux; events between frames can be missed |
| Attempt count | Explicit actual attempt-counter source | Successful insertion count |
| Successful insertion | Explicit admitted-particle counter/event with shared origin | Sticking or experimental arrival flux |
| Retained incident particles | Declared incident cohort, selection region and observation window | Bonding, incorporation or film quality without a separate criterion |
| Reflection | Explicit outward crossing/velocity/event definition and temporal evidence | A missing snapshot ID alone is insufficient |
| Escape/removal | Explicit boundary/event/removal source and cause | Normal physical escape versus unexpected lost atoms without evidence |
| Quantile height | Selected film-z quantile minus reference_z_angstrom | Density-based film thickness or epitaxial layer count |
| Grid roughness | RMS around the mean of occupied-cell maximum selected heights | Empty cells have zero height; grid coverage must be reported |
| Composition profile | All mapped species in explicit fixed-z bins; last bin includes its right edge | Structure phase or incorporation mechanism |
| Structural indicator | Requires selected phase/reference and calibration | No universal coordination/crystallinity threshold is supplied |

## Explicit trajectory time

`analyze_trajectory.py` accepts optional configuration time_segments. Each object declares id, first_frame, last_frame_exclusive, step_origin, time_origin_ps, timestep_ps and a nonempty source. Frame ranges use original input indices before stride and are ordered/nonoverlapping. Time is origin + (step-step_origin)*timestep. This can represent an explicitly reconciled restart step reset; no offset or timestep is guessed.

All read frames are checked, including frames skipped by stride. Supplied mappings must have strictly increasing finite physical time; repeated/decreasing time is a failure requiring explicit reconciliation. Gaps retain blank time/phase and UNMAPPED_FRAME; a complete geometry read with gaps reports PARTIAL_TIME_MAPPING. Omitting the mapping retains NOT_SUPPLIED and blank times. The source declaration is caller-supplied, not authenticated here. frame-metrics.csv and composition-profile.csv retain phase/time/status columns.

## Explicit balance origins

`analyze_balance.py` uses actual cumulative inserted/removed counters and observed counts. Optional counter_origins declares inserted and removed maps for every element plus source. With initial counts at the declared initial_time_ps:

`N_expected = N_initial + (inserted-inserted_origin) - (removed-removed_origin)`.

Rates use counter increments over the supplied physical-time interval and constant declared area. With origins omitted, the original tool contract uses zero origins; this is not automatic restart reconciliation. A source claim alone is not authenticated evidence. Decreasing counters or repeated/decreasing physical times are rejected. Missing actual counters are never reconstructed from snapshots. The tool reports raw cumulative counters, origins, since-origin differences and residuals, without repairing them. Removed counts have no automatic reflection/escape classification.

Counter rows now stream to a temporary disk spool rather than a Python row-history list. Input identity is checked before/after processing; changed sources and invalid counters are not committed as final output directories. Rates must remain finite. The final native CSV preserves every species/sample row; disk use grows with output length even though the row history is not retained in memory.

## Declared incident-event ledger

`tools/analyze_events.py --csv EVENTS.csv --config CONFIG.json --output-directory NEW_DIR` streams event evidence into events.sqlite with a bounded SQLite cache, plus cohort.csv, attempts.csv and events.json. CONFIG explicitly declares source_class (engineering_fixture/upstream_reference/research_output), scope_id, elements, start_time_ps, observation_time_ps, cohort_definition, counter_provenance and event_definitions for every supported event. No event detection, engine invocation or physical acceptance occurs.

CSV fields are event_id,time_ps,event,attempt_id,atom_id,element,source. Event/attempt/source identities must be nonempty; event IDs are unique. Times are ordered within the declared inclusive window. ATTEMPT has no atom ID; INSERTED resolves exactly one pending attempt to a unique positive atom ID. REJECTED resolves a pending attempt without admitting an atom. Atom IDs cannot be reused within this scope. Source events for substrate atoms or particles inserted before this window need a separately reconciled cohort.

| Event | Meaning in this bookkeeping adapter |
|---|---|
| ATTEMPT | Explicit actual attempt; never inferred from insertion count |
| REJECTED | Attempt ended without insertion |
| INSERTED | Actual admitted particle with attempt-to-atom mapping |
| REFLECTED | Declared qualifying crossing/history event; can occur more than once |
| ESCAPED | Explicit physical-removal/escape source, not a disappeared snapshot ID |
| REMOVED_UNKNOWN | Removal/loss has unresolved cause; cannot become normal escape |
| COHORT_RETAINED | Final membership of the declared region/cohort at exactly observation_time_ps |
| COHORT_NOT_RETAINED | Final nonmembership at that time, without inventing an escape cause |

Reflection history can overlap a retained or escaped particle; reflection events/unique reflected atoms are not an exclusive fate partition. Retention is not bonding, incorporation or a sticking coefficient. Missing final classifications, unresolved removals or pending attempts keep EVENT_LEDGER_PARTIAL. Retained-per-successful-insertion remains null when inserted-particle fates are incomplete. Duplicate events or inconsistent lifecycle transitions report FAILED and retain only earlier complete events in the labeled partial ledger. An event after final cohort observation/removal requires explicit reconciliation.

Exit 0 means a complete declared ledger summary, 1 partial/failed evidence, 2 input/SQLite/I/O/usage error. Actual event classifications and row sources remain caller-supplied, not authenticated by the ledger. If the selected engine/output does not supply attempts or reflection evidence, leave the gap explicit; do not manufacture those events from snapshots or successful insertion counters. Database/CSV/JSON artifacts preserve provenance and definitions for subsequent review.

Geometry supports orthogonal p/p/nonperiodic-z text dumps, including the explicitly supported Cartesian/scaled coordinate forms. Triclinic/rotated surface interpretation, arbitrary molecular topology and phase calibration require other evidence/adapters. Trajectory frames are streamed; no complete trajectory is held in memory. Per-frame atom and height-grid bounds remain explicit. Physical conclusions, sampling windows and method sensitivity still require review.
