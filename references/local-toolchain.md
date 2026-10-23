# Local structure, inputs, analysis and delivery

Use these helpers only within their stated adapters. Select explicit physical parameters and provenance; null template fields are unresolved decisions, not values to invent. All generated structures/inputs remain candidates, not engine, numerical or scientific acceptance. No helper attaches a calculator, evaluates energy/forces, submits jobs or launches LAMMPS.

## Dependencies and paths

The original six tools remain standard-library based. New structure tools use ASE/NumPy; trajectory and atomic-balance type-map validation also use ASE (trajectory calculations additionally use NumPy). Replica intervals use SciPy; plots use NumPy/Matplotlib; software previews use ASE's element validation, OVITO, PySide6-Essentials/QtGui and Matplotlib's packaged font. The integrated engineering demo uses those modules and the artificial fixtures shipped in `tests/`. Install only the modules needed in a separate research environment. The private project's exact lock is distinct from a generic compatible dependency declaration.

Configuration-relative source paths resolve beside the configuration, independently of the current working directory. Choose a new output directory outside the installed skill. Existing outputs are preserved. Source/configuration identities and method limits are retained. Failed trajectory/sweep preparations keep explicitly labeled partial outputs. Do not publish weights or local manifests into this public repository.

## Structure preparation

```text
python SKILL_ROOT/tools/prepare_structure.py --config CONFIG --output-directory NEW_DIRECTORY
python SKILL_ROOT/tools/audit_structure.py --structure FILE --format extxyz --type-order ELEMENTS --boundary p p f --minimum-separation VALUE --output NEW_JSON
```

Use `templates/structure-bulk.json`, `structure-slab.json`, or `structure-interface.json`:

- Cubic zincblende bulk: explicit ordered element pair, lattice constant with source and repeats. No default lattice constant, relaxation or phase judgment.
- Slab: a conventional periodic bulk, integer Miller indices, layer count, lateral repeats, explicit bottom/top plane trimming and plane tolerance. Reports observed top/bottom species, optionally checks requested top elements. This is an unreconstructed bare cut; it does not choose a low-energy termination, reconstruction or passivation.
- Interface: two axis-aligned orthogonal z-normal slabs. Explicitly chooses film strain to the substrate cell, gap, lateral shift, bottom buffer and upper vacuum, and reports the actual imposed lateral strain. Commensurate supercell search, rotated/triclinic interfaces and strain allocation to both materials are outside this adapter. Prepare needed repeats first; do not treat a stacked candidate as a stable interface.

The supported formats are extxyz, CIF and atomic LAMMPS data. LAMMPS data is interpreted with explicit metal units, type mapping and boundary; it cannot supply a boundary declaration itself. Export requires a cell already oriented in restricted lower-triangular LAMMPS form with positive diagonal; it rejects a cell that would otherwise be silently rotated by the writer. Generated data and extxyz preserve explicit type order, including unused mapped species. Audits check finite cell/coordinates/masses, nonperiodic bounds and pairs closer than a user-supplied threshold, with periodic images. A passed threshold is not a bond, energy or potential-suitability test. Candidate cut/strain choices still need scientific review.

## Fresh atomic-beam input packages

```text
python SKILL_ROOT/tools/prepare_input_package.py --config CONFIG --check-only --readiness-report NEW_JSON
python SKILL_ROOT/tools/prepare_input_package.py --config CONFIG --output-directory NEW_DIRECTORY
```

Use `templates/atomic-beam-input.json`. Supports metal units, atomic style, an orthogonal p/p/f box, nonempty disjoint fixed/bath groups and mobile atoms, explicit initial temperature/seeds/damping, timestep, stages, injection region above the initial surface, separate atomic beams and output/restart cadences. It renders one NVE integrator on mobile atoms (including the bath), Langevin forces on the static bath group, and deposit fixes assigning incoming atoms to mobile. Temperature DOF are explicit. This is a candidate integration/group contract awaiting engine tests, not validated insertion or thermal physics.

Both empirical and pretrained-ML routes supply documented literal `pair_style` and `pair_coeff` token lists and exact type order. File tokens `@potential_file:0`, `@potential_file:1`, etc. refer to listed existing files copied byte-for-byte into `models/`. `format: nep` also checks full header element coverage without cropping weights or adding ZBL. Header checks do not validate full weight format or accuracy. Retain model source and license references. No training or potential evaluation is performed.

Output includes `in.growth`, data/extxyz, type map, relocatable preparation configuration and an identity manifest. The prepared input uses package-relative files. Planned counts are intentions, not measured successful insertion/retention. Reaction precursors, molecular topology, general restart rendering, rotated cells and automated scientific approval are unsupported. Binary restart cadence is only a contract to test later; no binary restart is created locally. Engine/runtime, group/insertion/MPI behavior, actual pair syntax and physical validity remain unverified.

During the deposition phase, candidate thermo includes each deposit fix's documented cumulative insertion scalar; a tagged terminal print records the final value before those fixes are removed. Thermo fields are restored before unfix/post-relaxation. These are proposed runtime observations, not counters generated by local preparation. See release-matched [fix deposit output](https://docs.lammps.org/fix_deposit.html).

## Trajectory geometry and composition

```text
python SKILL_ROOT/tools/analyze_trajectory.py --trajectory DUMP --config CONFIG --output-directory NEW_DIRECTORY
```

Use `templates/trajectory-analysis.json`. Streams orthogonal text dumps one frame at a time, requiring positive unique atom IDs, explicit type mapping, finite coordinates, box and boundary. Accepts x/y/z, xu/yu/zu or xs/ys/zs; rejects unsupported triclinic cells. An explicit maximum atom count bounds local per-frame allocation. `--stride` and `--max-frames` make sampling visible; incomplete reads remain partial. Element labels, if present, must match numeric mapping.

For periodic x/y and nonperiodic z, explicitly select film elements, inclusive z window, reference z, height quantile and lateral grid. Outputs quantile z minus reference, occupied-grid maximum-height RMS, grid occupation fraction, snapshot species counts and a fixed-bin composition profile. Empty cells are excluded from roughness and their fraction reported. The last composition bin includes its right edge. These definitions are sensitive to grid/window and adatoms; occupation is not an automatic epitaxial coverage measure. ID differences between stored selected frames are neither deposition/escape counters nor a cumulative flux balance. No physical time, production window, phase/defect cutoff or interface definition is inferred.

### Explicit counter balance

`tools/analyze_balance.py --csv CSV --config CONFIG --output-directory NEW` uses `templates/atomic-balance.json`. Supply initial species counts, observed counts, actual cumulative inserted/removed columns sharing one origin, counter provenance, strictly increasing physical time and area. It checks initial + inserted − removed against observed and calculates interval counter-derived rates in atoms/angstrom²/ps. All counters are required; missing removal observations are not silently zeroed or reconstructed from snapshot ID gaps. Reconcile restart/reset phases explicitly before analysis. A balance match verifies supplied arithmetic, not counter authenticity, experimental flux equivalence or growth accuracy.

## Replica statistics, previews and reports

```text
python SKILL_ROOT/tools/summarize_replicas.py --csv CSV --config CONFIG --output-directory NEW_DIRECTORY
python SKILL_ROOT/tools/render_structure.py --structure FILE --format lammps-data --type-order ELEMENTS --label LABEL --output-directory NEW_DIRECTORY
python SKILL_ROOT/tools/generate_report.py --analysis-directory ANALYSIS --title TITLE --maximum-plot-points N --output-directory NEW_DIRECTORY
```

Replica configuration is `templates/replica-summary.json`: one explicitly independent scalar per replica/group, units, confidence and independence basis. Duplicate replica IDs and nonfinite values are rejected. Reports mean, sample SD, SEM and Student-t mean intervals; a single replica has no uncertainty estimate. Independence/normality and suitable per-run estimates are assumptions to assess, not established by the script. Correlated frames must not be supplied as independent replicas.

Previews use OVITO's Tachyon software renderer with a visible annotation band and portable font; they do not validate desktop GUI operation or physical structure. HTML reports embed PNG figures without external services and retain source class, methods and limits. Plot sampling is explicit and original CSV remains intact. No material result can be inferred from an engineering fixture.

## Candidate sweeps and local archives

```text
python SKILL_ROOT/tools/prepare_sweep.py --config CONFIG --maximum-candidates N --output-directory NEW_DIRECTORY
python SKILL_ROOT/tools/bundle_package.py --package-directory PACKAGE --archive NEW_ZIP --receipt NEW_JSON
```

Use `templates/candidate-sweep.json` with a bounded explicit variant list. The tool prepares proposed changes and each candidate audit, submits zero jobs and does not perform an implicit parameter grid. Partial preparation remains failed/partial. Changing a scientific parameter is a proposal requiring the appropriate plan decision.

The archiver includes only manifest-listed input files and the manifest. It rejects traversal/links/hidden files, verifies prepared identities, then checks ZIP CRC and archived member bytes against those identities. It does not transfer files, grant runtime permission or select outputs to discard. Keep keys and credentials out of research packages.

## Engineering acceptance example

```text
python SKILL_ROOT/tools/demo_local_pipeline.py --output-directory NEW_DIRECTORY
```

Creates artificial bulk/slab/stacked geometry, a literal inline-potential candidate, a two-frame fabricated trajectory, fabricated replica scalars, preview, report, archive and two unsubmitted variants. All values are test fixtures and all outputs label their scope. This validates local software behavior only; it never runs MD, infers forces, adopts a research orientation or proves semiconductor accuracy. Use it to check installation, not as a production template.
