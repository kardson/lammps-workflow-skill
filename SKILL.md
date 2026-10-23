---
name: lammps-md-workflow
description: Prepare, inspect, and analyze LAMMPS molecular dynamics workflows, especially semiconductor deposition with empirical or pretrained machine-learning potentials. Use for LAMMPS environment checks, potential selection, input review, run evidence, and result interpretation; excludes potential training.
metadata:
  short-description: Evidence-based LAMMPS deposition workflow
---

# LAMMPS MD workflow

Support natural-language research requests with traceable plans, actual inputs, and observed results. The repository root is the skill root. Resolve bundled tools and references from the absolute directory containing this file, independently of the current working directory. Store scientific work and machine-specific records in a separate, user-selected workspace.

## Route the current request

Enter at the relevant step; a status question does not require full onboarding. Read [capabilities](references/capabilities.md) to distinguish implemented helpers from agent-guided procedures. Reuse project instructions, scientific decisions, execution permissions, and collaboration choices. Do not introduce delegation or a persistent monitor by default.

- Environment/install/build: read [deployment](references/deployment.md). Compilation, executable help, numerical validation, and performance tests establish different facts. Never substitute a simulation for an environment check.
- Existing empirical or ML potential: read [potentials](references/potentials.md). Record exact identity, provenance, interface, species mapping, units and suitability evidence. Training, fine-tuning and active learning are outside this skill.
- Growth model, input preparation, or deposition analysis: read [deposition](references/deposition.md). Distinguish atomic/molecular beam insertion from reactive precursor chemistry. A command that inserts atoms does not establish CVD reaction physics.
- Local preparation or file diagnostics: read [local-first tools](references/local-first.md). Prefer local structure/text/data work; static input and log summaries do not substitute for target-runtime or numerical validation. Check scope fields and exit codes before reporting a parser result.
- Resume, run status, or result provenance: read [records](references/records.md). Historical running records do not justify a new launch; query the selected actual attempt once when asked. No generic SSH/launch adapter is shipped in this version.
- First installation or project connection: read [installation](references/installation.md). Installing a skill does not authorize changing unrelated project rules or global configuration.

## Research workflow

1. **Establish environment evidence.** Identify the selected executable, version, packages/styles, linked runtime, compute resources, potential file and analysis tools. Distinguish local controller from compute host. Mark missing or unverified facts and date observations; old receipts are not live readiness.
2. **Clarify the question and materials.** Preserve the user's choices. Resolve result-changing gaps such as growth mechanism, composition, crystal orientation/termination, source structures, surface state and observable. Draft with explicit unknowns while awaiting answers; do not silently choose scientific parameters.
3. **Agree the plan.** Describe potential suitability, geometry, boundaries, stages, timestep, physical duration, insertion schedule, thermostat/heat removal, repeats, requested outputs, restart contract, validation and stop conditions. Templates are unconfirmed drafts, not authorization.
4. **Prepare and inspect actual inputs.** Compare actual files against the agreed plan: type-to-element order, masses, units, atom style, potential identity and interface syntax, groups, constraints, injection region/velocity, box, output and restart settings. Archive the audit with the relevant plan and authorization. Mechanical checks do not prove numerical stability or potential validity.
5. **Execute only the authorized scope.** Preserve separate attempt directories and launch identity. Check genuine startup/progress once, deliver a receipt, and let ordinary host programs record subsequent state. Query or monitor only as requested. Reuse existing authorization within scope; installation/build permission alone does not permit MD or benchmarking. Do not alter another calculation, MPI installation, driver or multiplexer session.
6. **Interpret evidence.** Establish what actually ran and completed before claiming results. Check atom balance, physical time, stability, temperature definition, equilibration/production selection, growth observables, uncertainty, replicas and provenance. Separate observations, interpretations, limitations and researcher acceptance. Missing preparation or outputs permit bounded diagnostics labeled partial, not accepted scientific results. Program exit success is not scientific acceptance.

## Core limits

Use the exact manual and potential-interface documentation matching the installed versions. Empirical multi-component interactions and ML applicability must be justified for the target system; element coverage alone is insufficient. Do not invent mixing rules or repair a multi-element NEP model by truncating its element header. CPU and GPU interfaces may use different syntax and precision and require their own numerical comparison.

Keep scientific records out of the installed skill. Never fabricate approvals or retrospectively turn a draft into a confirmed plan. Preserve raw outputs and distinguish run completion, numerical validity, and scientific acceptance. Resume from actual evidence and the user's latest scope, without duplicate launches or continuous polling.
