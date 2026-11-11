# External fields and deposition

Use this route when fields are part of the research question. It provides
agent-guided planning and source checks, not a field-aware engine, model loader,
field-input generator or validated material-response model.

## Choose the physical coupling before input syntax

| Intended effect | Evidence required | What does not establish it |
|---|---|---|
| Charged arriving-species transport | Charge states/fractions, field map, gas/collision model and integrator | Assigning arbitrary charge to neutral atoms |
| Polarization or field-dependent surface energetics | Existing response-capable weights/parameterization, exact interface and target validation | Ordinary coordinate-only ML potential plus `fix efield` |
| Magnetic material response | Appropriate magnetic degrees of freedom/model and reference evidence | Installing SPIN or using an electric-response model |
| Field-altered incident distribution | Traceable transport-to-surface flux/composition/energy-angle boundary | Claiming intrinsic surface-barrier changes from altered arrivals alone |

LAMMPS `fix efield` acts on declared charges/dipoles; it does not supply a
semiconductor electronic-polarization model. A coordinate-only NEP does not become
qNEP or spin-aware because a library exposes another compute overload. Check the
actual weights and the native pair call. Preserve empirical and pretrained-ML
options; each needs the required cross interactions and physical response.

For close-spaced sublimation, source/gap transport and the surface-MD arrival
boundary are separate modeling levels. Identify relevant vapor species and
arrival distributions from evidence; an atomic insertion script does not
establish a CSS transport model. A strained single-material proxy cannot silently
stand in for the chemistry of a different multicomponent substrate/interface.

## Existing response-model candidates

Inspect actual released artifacts, provenance and terms before choosing a
runtime. Framework support, training scripts and a universal model name do not
establish an available suitable checkpoint; training remains outside this skill.
Element coverage, head/property availability, interface compatibility and target
accuracy are separate claims. Check checkpoint metadata rather than inferring
it from a neighboring training log. Code and weights may have different terms.

MACE-Field publishes existing electric-response models and LAMMPS/ML-IAP
examples. At code commit `45d5c5fa7b40a155855b3d155df1760e36849e64`, the
ML-IAP wrapper reads a uniform electric-field vector from a per-process
environment variable. The export script defaults to libtorch; its explicit
ML-IAP route enables additional cuequivariance dependencies. Specify and verify
the model head and precision; a default last head may be inappropriate. These
source observations do not validate a local installation, open-boundary
insertion, a particular material, or magnetic response. Verify the selected
release and local version again when implementing it.

qNEP/BEC and NEP_Spin are distinct model/runtime routes. Appropriate response
weights are required; ordinary NEP weights are not interchangeable. Development
documentation is not proof of support in an installed LAMMPS pair style.

## Field protocol and validation

Record frame/axis relative to the surface, vector sign/direction, spatial region,
units and time law. For AC include amplitude convention, waveform, frequency,
offset, phase and ramp. Research-variable ranges can remain unresolved during
preparation; do not demand one fixed strength if strength/direction are the study
variables. Preserve explicitly deferred surface studies while requiring an
identified baseline surface before interpreting its results.

Validation follows the selected mechanism and branch:

- Establish no-field target-domain behavior and independently comparable labels.
- For electric response, verify coordinate/field derivatives, conventions and
  units before evaluating target accuracy. Keep bulk periodic and open-surface
  electric-boundary references distinct. Avoid double-counting a learned field
  coupling with an added force.
- Compare reference-calculator and LAMMPS energies/forces for the same geometry,
  field, head and precision; separately check open boundaries, changing atom
  counts, neighbor rebuilds and selected MPI paths.
- Log the field at actual force-evaluation times, including initialization.
  An end-of-step environment update is read by a later force call, not
  automatically the intended current-time field. Check timestep refinement,
  all-rank consistency, physical clock and restart phase. A process-local
  environment change does not broadcast itself to other MPI processes.
- Include external work and thermostat heat in a time-dependent-field energy
  balance; ordinary NVE energy conservation is not its criterion.
- For Lorentz-only transport, check zero force for zero charge or velocity
  parallel to B and no work by magnetic force. These limits do not imply absence
  of neutral-material polarization or magnetic response through other mechanisms.

Thresholds and resources need explicit sources before a run. Preserve partial
states when reference labels, field ranges, mechanisms or authorization are
missing. An unresolved magnetic branch need not prevent no-field/electric
preparation. Field-driven inference/MD requires its own applicable authorization;
installation and source inspection do not grant it.

For growth comparisons, distinguish changed arrival conditions from direct
surface response. Calibrate stable-nucleus/cluster and persistence criteria,
coalescence, net atom balance and crystal classification; retain independent
replicas, censored waiting times and accelerated-flux/time-scale limits. Use
[validation cases](validation-cases.md), [stage contracts](stage-contracts.md)
and [uncertainty](uncertainty.md) for existing record/analysis support. They do
not supply the missing field physics or scientific acceptance.

## Primary sources (reviewed 2026-11-11)

- [LAMMPS electric force](https://docs.lammps.org/fix_efield.html)
- [LAMMPS spin precession](https://docs.lammps.org/fix_precession_spin.html)
- [GPUMD field interface, development](https://gpumd.org/dev/gpumd/input_parameters/add_efield.html)
- [GPUMD spin model, development](https://www.gpumd.org/dev/potentials/nep_spin.html)
- [MACE-Field pinned code and interface](https://github.com/mdi-group/mace-field/tree/45d5c5fa7b40a155855b3d155df1760e36849e64)
- [MACE-Field reproduction assets and erratum](https://github.com/mdi-group/2025-04-mace-field/releases/tag/resubmitted)

Use manuals matching the actual selected runtime. No linked weights, datasets,
source code or third-party manual text are bundled here.
