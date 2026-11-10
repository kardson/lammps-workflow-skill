# Engine combinations and site bindings

Use engine-profile.json for software versions, interfaces, patches, backend, precision, runtime requirements and evidence. Keep actual executable paths and connection references in private site-binding.json instances. Null revision fields are unresolved; do not invent them from an executable filename.

The controller retains its selected Python environment and dependency lock. CPU NEP and GPU MatPL are distinct engine profiles; a shared model does not make their syntax or binary restart formats interchangeable. Keep the repaired GPU profile separate from the original profile. Existing native NEP execution does not require adding Torch or migrating the controller runtime.

Site bindings record dated resource observations, not guaranteed current free resources. Reading a profile never sources shell configuration, connects, installs, imports optional runtimes or launches a calculation. Preserve existing VASP environments and workload constraints. Live readiness requires a separately scoped observation.
