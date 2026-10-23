# Environment and deployment

## Evidence layers

Keep separate observations for controller tools, compute host, installed engine, numerical behavior and performance. Date the host observation and record actual executable paths and versions privately. Reuse unchanged evidence, but do not describe an offline or upgraded workstation from dated receipts as currently ready.

The controller can provide ASE, NumPy/SciPy, pandas/Matplotlib, OVITO and Jupyter in a dedicated Python environment. spglib is useful for periodic bulk symmetry, not a general surface/defect classifier. Install only needed modules and record a local lock. Python and desktop OVITO may have different compatible versions. A version query does not validate 3D graphics.

On a compute host, check the chosen LAMMPS release, compiler/CMake, MPI build/runtime/launcher, shared libraries, required package/style registration, memory/disk and active resource constraints. For GPU use, also record driver visibility, toolkit/compiler support for the actual architecture, KOKKOS/interface compatibility and precision. A CUDA-capable card and a built GPU package do not accelerate an arbitrary CPU potential interface.

## Isolated installation

Use separate source, build, install and attempt directories. Avoid replacing dependencies used by an existing workload. On Windows/WSL, follow the GPU vendor's WSL instructions; do not install a Linux display driver inside WSL as an MD dependency. Choose CPU/MPI and GPU backend combinations on documented compatibility, then observe actual support. Do not assert a platform or dual-socket configuration is faster without representative measurements.

Installation and compilation can be authorized independently of calculations, including while another calculation is running if the user's permission and resource constraints allow. Never impose a universal rule that any VASP process forbids compilation; never treat build permission as permission for MD, static energy/force calculations or benchmarking.

The bundled environment tool invokes only bounded version queries and optionally `lmp -h`. Linked-library inspection and plugin-specific initialization require an explicit, platform-appropriate follow-up. Use exact help sections to check names and report unavailable information; these checks cannot prove dynamic insertion, MPI consistency or restart correctness.

## Numerical acceptance when authorized

Agree thresholds before testing: empirical short case; fixed-structure model inference; CPU/GPU energy, force and needed virial comparison; single/multiple rank behavior; open surface and changing atom count; restart continuity. Performance measurements are a separate permission and acceptance layer. Keep failed combinations as failed candidates, preserving logs and patch provenance.

Official sources: [LAMMPS build](https://docs.lammps.org/Build.html), [packages](https://docs.lammps.org/Packages.html), [acceleration](https://docs.lammps.org/Speed_packages.html), [NVIDIA WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html). Use release-matched documentation for actual builds.
