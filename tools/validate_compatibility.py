"""Read-only query of recorded model/engine/scenario evidence."""
import argparse
import json
from compatibility_registry import load_evidence, query


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--model-sha256', required=True)
    parser.add_argument('--engine-id', required=True)
    parser.add_argument('--scenario', required=True)
    args = parser.parse_args()
    try:
        report = query(load_evidence(args.evidence), args.model_sha256, args.engine_id, args.scenario)
    except (ValueError, OSError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error)}))
        return 2
    print(json.dumps(report, indent=2))
    return 1 if any(item['status'] in ('FAILED', 'CONFLICTING') for item in report['dimensions'].values()) else 0


if __name__ == '__main__':
    raise SystemExit(main())
