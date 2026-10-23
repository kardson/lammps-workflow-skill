# Install and connect

The public repository root is the complete `lammps-md-workflow` skill. When asking a skill installer to install from GitHub, use:

```text
repo: kardson/lammps-workflow-skill
path: .
name: lammps-md-workflow
```

Alternatively clone/copy the complete repository into the host's installed skills directory under `lammps-md-workflow`. Keep tools, references, templates and metadata beside `SKILL.md`. Discoverability may require a new session or a skill-catalog refresh depending on the host. Do not claim that installation upgraded a LAMMPS executable.

Select a separate research workspace. Existing layouts and project instructions take precedence. To create a new layout, invoke the installed tool by its absolute path:

```text
python ABSOLUTE_SKILL_ROOT/tools/init_workspace.py --workspace ABSOLUTE_RESEARCH_ROOT
```

The tool creates missing directories and a draft plan/model card, preserving existing files. Adding a project route is opt-in through `--connect-skill`; use that only when the user's project-connection request authorizes editing its AGENTS.md. Installation alone is not authorization to edit unrelated workspaces or global instructions. The appended route keeps other project rules intact and doesn't grant execution permissions.

Use the skill naturally for LAMMPS tasks or invoke `$lammps-md-workflow`. Read only relevant references and preserve the existing collaboration mode. Single-agent work requires no extra mode-selection dialogue. Updates should stage and compare the new skill against the installed one; preserve local adaptations and retain the previous version before an authorized activation.

The skill's standard-library tools require Python 3.10+. Geometry, notebooks, visualization and real execution need separately installed tools and project-specific paths. See [deployment](deployment.md). Private settings, local caches, weights and raw outputs are never part of the skill installation.
