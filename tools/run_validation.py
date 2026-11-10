"""Plan validation selection or parse existing evidence; no implicit execution."""
import argparse
import json
from validation_cases import load_case, plan, parse_termination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation', required=True, choices=['plan', 'parse'])
    parser.add_argument('--case', required=True, action='append')
    parser.add_argument('--category', action='append', choices=['installation', 'inference', 'md', 'performance', 'scientific', 'local_logic'])
    parser.add_argument('--result-directory')
    args = parser.parse_args()
    try:
        cases = [load_case(path) for path in args.case]
        if args.operation == 'plan':
            if args.result_directory:
                raise ValueError('Result directory is only used by parse')
            result = plan(cases, args.category)
            code = 0
        else:
            if len(cases) != 1 or not args.result_directory or args.category:
                raise ValueError('Parse requires exactly one case and a result directory; no category selection')
            result = parse_termination(cases[0], args.result_directory)
            code = 0 if result['status'] == 'PASSED' else 1
    except (OSError, ValueError, ImportError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error)}))
        return 2
    except Exception as error:
        # jsonschema errors are optional-dependency types; preserve structured failure.
        if error.__class__.__module__.startswith('jsonschema'):
            print(json.dumps({'status': 'ERROR', 'message': str(error)}))
            return 2
        raise
    print(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
