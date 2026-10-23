"""Create missing workspace records, optionally append a local skill route."""
import argparse
import json
from pathlib import Path

from common import SKILL_ROOT

DIRECTORIES = ['01_plan', '02_literature', '03_models', '04_runs', '05_analysis', '06_review', '99_admin']
MARKER = '## LAMMPS workflow skill'
ROUTE = '''

## LAMMPS workflow skill

For LAMMPS research tasks, use the installed `lammps-md-workflow` skill.
Find its SKILL.md through the host skill catalog; enter at the relevant step.
Keep this private research workspace separate from the installed public skill.
Preserve existing scientific decisions, collaboration mode and execution permissions.
Installation or compilation is not permission for MD, benchmarks or monitoring.
If the skill is unavailable, report that gap and use existing project rules.
'''


def initialize(workspace, connect_skill=False):
    workspace = Path(workspace).expanduser()
    if not workspace.is_absolute():
        raise ValueError('Select an absolute independent research workspace.')
    workspace = workspace.resolve()
    if workspace.is_relative_to(SKILL_ROOT):
        raise ValueError('Research workspace must be outside the installed skill.')
    created, preserved = [], []
    for name in DIRECTORIES:
        (workspace / name).mkdir(parents=True, exist_ok=True)
    for template, target in [('plan.json', '01_plan/md-plan.json'),
                             ('model-card.json', '03_models/model-card.json')]:
        destination = workspace / target
        if destination.exists():
            preserved.append(target)
            continue
        content = (SKILL_ROOT / 'templates' / template).read_text(encoding='utf-8')
        with destination.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
        created.append(target)
    if connect_skill:
        rules = workspace / 'AGENTS.md'
        previous = rules.read_text(encoding='utf-8') if rules.exists() else ''
        if MARKER not in previous:
            with rules.open('a', encoding='utf-8', newline='\n') as stream:
                stream.write(ROUTE)
            created.append('AGENTS.md: LAMMPS route appended')
        else:
            preserved.append('AGENTS.md: existing LAMMPS route')
    return {'workspace': str(workspace), 'created': created, 'preserved': preserved,
            'scientific_confirmation': None, 'execution_permission_granted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--connect-skill', action='store_true', help='Append project route only with project-edit authorization')
    args = parser.parse_args()
    print(json.dumps(initialize(args.workspace, args.connect_skill), indent=2))


if __name__ == '__main__':
    main()
