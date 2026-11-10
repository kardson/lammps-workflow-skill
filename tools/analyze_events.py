"""Analyze declared incident-particle event evidence locally; no trajectory inference."""
import argparse
import json
import sqlite3

from deposition_events import analyze
from local_common import load_config, resolve_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    try:
        config, _ = load_config(args.config)
        report = analyze(resolve_file(args.csv, '.'), config, args.output_directory)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'simulation_run': False}))
        return 2
    print(json.dumps({'status': report['status'], 'events_processed': report['events_processed'],
                      'elements': report['elements'], 'simulation_run': False}))
    return 0 if report['status'] == 'DECLARED_EVENT_LEDGER_SUMMARY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
