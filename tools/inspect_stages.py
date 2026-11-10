"""Audit a declared phase contract or inspect one supplied observation; no monitoring."""
import argparse
import json
from pathlib import Path

from stage_contract import audit, inspect_observation


def read(path):
    path = Path(path)
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Stage/observation JSON exceeds 4 MiB bound')
    def reject(value):
        raise ValueError('Nonfinite JSON token unsupported: ' + value)
    return json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=reject)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--observation')
    parser.add_argument('--stage')
    parser.add_argument('--reference-root')
    args = parser.parse_args()
    try:
        if bool(args.observation) != bool(args.stage):
            raise ValueError('Observation and stage must be supplied together')
        contract = read(args.contract)
        if args.observation:
            result = inspect_observation(contract, args.stage, read(args.observation))
            code = 1 if result['status'] in ('UNVERIFIED', 'CONDITION_TRIGGERED') else 0
        else:
            result = audit(contract)
            code = 1 if result['status'] in ('INVALID', 'PARTIAL') else 0
        if args.reference_root and result.get('status') != 'INVALID':
            from stage_links import check
            result['source_links'] = check(contract, args.reference_root)
            if result['source_links']['status'] != 'LINKS_MATCH_RECORDED_EVIDENCE':
                code = 1
    except (OSError, ValueError, ImportError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'process_action_performed': False}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
