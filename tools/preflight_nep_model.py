"""Reject mismatched NEP identity/element headers before an authorized launch.

Read-only, standard-library only. JSON goes to stdout; no engine is launched.
"""
import argparse
import json
import re

from inspect_potential import inspect_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--elements', nargs='+', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-fA-F]{64}', args.expected_sha256):
        parser.error('Expected SHA-256 must contain 64 hexadecimal characters')
    problems = []
    report = {'status': 'REJECTED', 'model': args.model, 'inference_run': False}
    try:
        observed = inspect_file(args.model, 'nep', args.elements)
        report['observed'] = observed
        if observed['sha256'] != args.expected_sha256.lower():
            problems.append('Model SHA-256 differs from selected identity')
        missing = [element for element, covered in observed['required_element_coverage'].items() if not covered]
        if missing:
            problems.append('Required elements absent: ' + ', '.join(missing))
    except (OSError, UnicodeError, ValueError) as error:
        problems.append(str(error))
    report.update(status='REJECTED' if problems else 'PASS', problems=problems,
                  scope='Stable file identity and NEP element header only; no full format, numerical or scientific acceptance.')
    print(json.dumps(report, indent=2))
    return 2 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
