# Empirical and pretrained ML potentials

Record candidates in `templates/model-card.json`. Keep potential identity distinct from interface identity: file source/version/license/hash, supported elements, training/fit domain and published validation; interface repository/commit, actual LAMMPS version, pair syntax, CPU/GPU, precision, MPI and dynamic-atom/restart behavior. Missing evidence remains unverified.

## Empirical route

Check all required species and cross interactions for the exact parameterization, plus units, atom style, charges/topology and needed packages. A name such as Tersoff, SW, BOP or MEAM denotes a model family, not a suitable multi-component parameter set. Do not invent missing cross terms or use `hybrid`/mixing as an automatic substitute for interface chemistry.

## Pretrained ML route, including NEP89

Use original weights with provenance and license; never train, fine-tune or initiate active learning in this workflow. For a multi-element NEP file, preserve the full model and header. Checking that desired elements occur in the header establishes coverage only. Do not truncate the header/weights to a four-element model. Inspect any built-in short-range correction such as ZBL before adding a second correction.

NEP_CPU and MatPL/NEP KOKKOS are independent integration routes. Check their exact `pair_style` / `pair_coeff` documentation and species mapping; do not swap executables and assume syntax or numerics are interchangeable. Upstream version declarations do not prove compatibility with later LAMMPS/KOKKOS types or a different GPU architecture.

For growth, seek evidence for bulk phases, surface reconstructions, strain, interfaces, adsorption/diffusion and arriving species/energies as relevant. Reactive precursors need the relevant chemical species and reaction coverage. Where evidence is absent, propose validation or a narrower claim; a universal model name does not establish target-system accuracy.

Sources: [LAMMPS potential guidance](https://docs.lammps.org/pair_style.html), [NIST repository](https://www.ctcms.nist.gov/potentials/), [NEP_CPU](https://github.com/brucefan1983/NEP_CPU), [GPUMD](https://github.com/brucefan1983/GPUMD), [MatPL LAMMPS interface](https://github.com/LonxunQuantum/lammps-MatPL). Check the exact interface release before preparing executable input.
