"""Inspect an explicitly mapped structure without a calculator."""
import argparse

from common import evidence_path, print_receipt, utc_now, write_report
from local_common import identity
from structure_io import geometry_summary, read_structure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--structure', required=True)
    parser.add_argument('--format', choices=['extxyz', 'cif', 'lammps-data'], required=True)
    parser.add_argument('--type-order', nargs='+', required=True)
    parser.add_argument('--boundary', nargs=3, required=True)
    parser.add_argument('--minimum-separation', type=float, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = evidence_path(args.output)
    source = identity(args.structure)
    atoms = read_structure(args.structure, args.format, args.type_order, args.boundary)
    report = geometry_summary(atoms, args.type_order, args.boundary, args.minimum_separation)
    report.update(observed_utc=utc_now(), source=source, calculator_used=False, scientific_acceptance='UNVERIFIED')
    write_report(output, report)
    print_receipt(output, geometry_checks_passed=report['geometry_checks_passed'], atom_count=len(atoms))
    if not report['geometry_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
