"""Fingerprint an existing potential; optional NEP header check, no inference."""
import argparse
import hashlib
from pathlib import Path
import re

from common import evidence_path, print_receipt, utc_now, write_report


def inspect_file(path, kind, required):
    path = Path(path).expanduser().resolve(strict=True)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Potential changed during inspection; reacquire stable evidence.')
    report = {'observed_utc': utc_now(), 'path': str(path), 'kind': kind,
              'bytes': after.st_size, 'sha256': digest.hexdigest(),
              'scientific_suitability': 'UNVERIFIED', 'inference_run': False,
              'scope': 'Exact file identity and optional header coverage; weights/format completeness and numerical suitability not validated.'}
    if kind == 'nep':
        with path.open('r', encoding='utf-8') as stream:
            header = stream.readline(65536).split()
        if len(header) < 3 or not re.fullmatch(r'nep\d+(?:_zbl)?', header[0]):
            raise ValueError('Unrecognized NEP header; preserve the original file for inspection.')
        count = int(header[1])
        elements = header[2:]
        if count <= 0 or len(elements) != count or len(set(elements)) != count:
            raise ValueError('NEP element count or uniqueness does not match the header.')
        report.update(format=header[0], element_count=count, elements=elements,
                      required_element_coverage={element: element in elements for element in required},
                      built_in_zbl_declared=header[0].endswith('_zbl'))
    elif required:
        raise ValueError('Element coverage requires --kind nep; empirical metadata is not inferred.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file')
    parser.add_argument('--kind', choices=['nep', 'empirical', 'other-ml'], required=True)
    parser.add_argument('--require-element', action='append', default=[])
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = evidence_path(args.output)
    report = inspect_file(args.file, args.kind, args.require_element)
    write_report(output, report)
    covered = all(report.get('required_element_coverage', {}).values())
    print_receipt(output, required_element_coverage_passed=covered if args.require_element else None)
    if not covered:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
