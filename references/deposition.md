# Deposition planning, input checks and analysis

## Scientific decisions

Distinguish atomic beam, molecular beam and reactive precursor deposition. Clarify substrate/growth species, crystal orientation and termination, surface reconstruction/passivation, composition, source structures, lattice/strain convention, lateral size, substrate thickness, free space and boundaries. Existing DFT choices are evidence to discuss, not MD approval.

Agree arrival species/mixture, position/region, velocity or incident energy/angular distribution, schedule/flux, random seeds and repeats. Relate arrival rate to simulated area and physical time. Accessible MD time and elevated flux can change mechanisms; state the intended interpretation and limitations. Do not insert default temperatures, time steps or fluxes as confirmed values.

## Input audit

- Explicit units, atom style, masses and type-to-element order consistent with the potential interface and all generated files.
- Potential bytes and model card; relevant short-range behavior and cutoff; no duplicated correction or invented interactions.
- Cell, periodic directions, surface normal, fixed/bath/mobile groups, initial overlaps, injection region and escape handling.
- New atoms receive the intended integration and thermal treatment; group membership, compute temperature degrees of freedom and atom-count changes match the selected LAMMPS release. Inspect relevant command semantics rather than imposing one group/thermostat recipe.
- Thermostat regions remove heat without unintentionally damping the incident beam or prescribing unsupported surface dynamics. Account for fixed atoms, streaming and changing population in temperature definitions.
- Step count and physical time, insertion/relaxation stages, thermo and trajectory cadence, stable atom IDs/type fields, restart cadence and restart source/compatibility.

Dynamic insertion requires interface-specific tests after authorization. Help registration or a successful static model evaluation cannot establish allocation growth, atom migration, neighbor rebuild or restart safety.

## Interpretation

Track initial + inserted − deleted/escaped atom balance with the agreed definition, physical time and incident/deposited counts. Unexpected lost atoms require diagnosis; intended escape handling is a separately recorded boundary choice. Inspect temperature, energy trends and integration stability using criteria appropriate to the non-equilibrium growth process; do not apply closed-system NVE energy conservation blindly to injection/thermostatted runs.

Define film thickness, roughness, composition/stoichiometry, mixing, coverage, coordination, defects and crystallinity before analyzing them. Record spatial selection, reference surface, cutoffs, frame window and estimator. Bulk CNA/PTM labels do not alone characterize a multi-component semiconductor surface or interface. Separate transient growth, relaxation and any stationary production window.

Assess seed dependence, finite size, accessible time, force-field limitations and statistical uncertainty. A visually plausible film or successful run is not experimental growth-rate or epitaxial-quality validation.

Sources: release-matched [fix deposit](https://docs.lammps.org/fix_deposit.html), [compute_modify](https://docs.lammps.org/compute_modify.html), [boundary](https://docs.lammps.org/boundary.html), [write_restart](https://docs.lammps.org/write_restart.html). These links are entry points, not evidence that an untested input is valid.
