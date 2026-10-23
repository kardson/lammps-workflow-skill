"""Observe the current host and optional LAMMPS help; never run an MD input."""
import argparse
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

from common import evidence_path, print_receipt, utc_now, write_report


def parse_help(text):
    result = {}
    headings = list(re.finditer(r'(?m)^\*\s+([^:\n]+styles):\s*$', text))
    for i, match in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        result[match.group(1)] = sorted({token.rstrip('*') for token in text[match.end():end].split()
                                       if token != '(none)'})
    package_match = re.search(r'Installed packages:\s*\n(.*?)(?=\n\s*Lists of individual styles|\Z)', text, re.S)
    result['packages'] = sorted(set(package_match.group(1).split())) if package_match else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=['controller', 'workstation'], required=True)
    parser.add_argument('--lmp', help='Explicit chosen binary or command name; called with -h only')
    parser.add_argument('--package', action='append', default=[])
    parser.add_argument('--pair-style', action='append', default=[])
    parser.add_argument('--fix-style', action='append', default=[])
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = evidence_path(args.output)
    versions = {}
    for name in ['ase', 'numpy', 'scipy', 'pandas', 'matplotlib', 'ovito', 'spglib', 'jupyterlab']:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    engine = {'status': 'UNVERIFIED', 'reason': 'No executable selected.'}
    if args.lmp:
        binary = shutil.which(args.lmp)
        if not binary:
            engine = {'status': 'MISSING', 'selected': args.lmp}
        else:
            try:
                result = subprocess.run([binary, '-h'], stdin=subprocess.DEVNULL,
                                        capture_output=True, text=True, errors='replace', timeout=30)
                help_text = result.stdout + result.stderr
                sections = parse_help(help_text)
                requirements = {'packages': args.package, 'Pair styles': args.pair_style,
                                'Fix styles': args.fix_style}
                checks = {section: {name: (name in sections[section] if sections.get(section) is not None else None)
                                    for name in names} for section, names in requirements.items()}
                engine = {'status': 'OBSERVED' if result.returncode == 0 else 'FAILED',
                          'binary': str(Path(binary).resolve()), 'help_exit': result.returncode,
                          'sections': sections, 'requested_membership': checks, 'help': help_text}
            except (OSError, subprocess.TimeoutExpired) as error:
                engine = {'status': 'UNVERIFIED', 'binary': binary, 'reason': str(error)}
    report = {'observed_utc': utc_now(), 'role': args.role, 'system': platform.platform(),
              'python': platform.python_version(), 'visible_logical_cpus': os.cpu_count(),
              'installed_distributions': versions, 'engine': engine,
              'scope': 'Package metadata and selected executable help only; not imports, linking, numerical validity or full readiness.',
              'simulation_run': False, 'performance_test_run': False}
    write_report(output, report)
    print_receipt(output, engine_status=engine['status'])
    # Missing requested capabilities are reported without treating absent evidence as success.
    checks = engine.get('requested_membership', {})
    failed = any(value is not True for section in checks.values() for value in section.values())
    if args.lmp and (engine['status'] != 'OBSERVED' or failed):
        raise SystemExit(1)
    if not args.lmp and (args.package or args.pair_style or args.fix_style):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
