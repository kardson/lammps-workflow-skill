"""Validate a v1 record structurally. No input execution or remote access."""
import argparse
import json
from pathlib import Path
import sys
import hashlib
from record_io import read_record, reference_path

SCHEMAS = Path(__file__).resolve().parents[1] / 'schemas'
KINDS = {'md_plan': 'plan', 'potential_model_card': 'model-card',
         'execution_attempt': 'attempt', 'decision_log': 'decision-log'}


def validate_links(record, base):
    """Check explicit local references only; never interpret LAMMPS commands."""
    errors, unknown = [], []

    def check_identity(item, path_key='file'):
        if not isinstance(item, dict):
            errors.append('File identity must be an object')
            return
        raw = item.get(path_key)
        if not raw:
            unknown.append('Missing file identity path')
            return
        if not isinstance(raw, str):
            errors.append('Identity path must be a string')
            return
        path = (base / raw).resolve()
        if not path.is_file():
            errors.append('Missing file: ' + str(raw))
            return
        expected = item.get('sha256')
        if expected is not None and (not isinstance(expected, str) or len(expected) != 64
                                    or any(c not in '0123456789abcdefABCDEF' for c in expected)):
            errors.append('Expected SHA256 must be 64 hexadecimal characters')
            return
        if expected:
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest().lower() != expected.lower():
                errors.append('SHA256 mismatch: ' + str(raw))
        else:
            unknown.append('Missing expected SHA256: ' + str(raw))
        if item.get('bytes') is not None and path.stat().st_size != item['bytes']:
            errors.append('Size mismatch: ' + str(raw))

    if record.get('record_type') == 'potential_model_card':
        check_identity(record['identity'])
        mapping = record.get('type_to_element')
        if isinstance(mapping, list):
            if not all(isinstance(value, str) for value in mapping):
                errors.append('Type mapping entries must be element strings')
            elif not set(mapping).issubset(set(record.get('elements', []))):
                errors.append('Type mapping includes elements absent from model declaration')
        else:
            unknown.append('Type mapping is unresolved or unsupported representation')
    elif 'package_files' in record:
        listed = record['package_files']
        identities = record['file_identities']
        names = [item.get('package_file') for item in identities]
        if len(set(listed)) != len(listed) or len(set(names)) != len(names) or set(listed) != set(names):
            errors.append('Package inventory and identity entries disagree or contain duplicates')
        for item in identities:
            raw = item.get('package_file')
            if not raw or not (base / raw).resolve().is_relative_to(base.resolve()):
                errors.append('Package member escapes package directory')
                continue
            check_identity(item, 'package_file')
    else:
        for field in ('plan', 'input_audit', 'model_card'):
            raw = record.get(field)
            if isinstance(raw, str) and not (base / raw).is_file():
                errors.append('Missing reference ' + field + ': ' + raw)
        if record.get('record_type') == 'md_plan':
            raw = record.get('model', {}).get('model_card')
            if isinstance(raw, str) and not (base / raw).is_file():
                errors.append('Missing model_card reference: ' + raw)
        binding = record.get('plan_binding')
        if binding is not None:
            if not isinstance(binding, dict) or not isinstance(binding.get('file'), str):
                errors.append('plan_binding requires an object with a file path')
            else:
                check_identity(binding)
                path = base / binding['file']
                if path.is_file():
                    try:
                        plan = read_record(path)
                        if not isinstance(plan, dict) or plan.get('record_type') != 'md_plan':
                            errors.append('Bound file is not an md_plan')
                        else:
                            for key in ('id', 'schema_version'):
                                if key not in binding:
                                    unknown.append('Plan binding missing ' + key)
                                elif binding[key] != plan.get(key):
                                    errors.append('Plan binding mismatch: ' + key)
                            declared = record.get('input_declarations')
                            if isinstance(declared, dict):
                                simulation = plan.get('simulation', {})
                                for key in ('units', 'atom_style', 'boundary', 'type_to_element', 'timestep'):
                                    if key not in declared or simulation.get(key) is None:
                                        unknown.append('No comparable plan/input declaration: ' + key)
                                    elif declared[key] != simulation[key]:
                                        errors.append('Plan/input declaration mismatch: ' + key)
                                unknown.append('Input declarations are not verification of actual LAMMPS script behavior')
                            else:
                                unknown.append('No input_declarations supplied for plan comparison')
                    except (ValueError, OSError) as error:
                        errors.append('Cannot read bound plan: ' + str(error))
        elif record.get('record_type') == 'execution_attempt':
            unknown.append('No immutable plan_binding supplied')
        if record.get('record_type') == 'execution_attempt':
            model_ref = record.get('model_card')
            if isinstance(model_ref, str) and (base / model_ref).is_file():
                try:
                    model = read_record(reference_path(base / 'record.json', model_ref))
                    if not isinstance(model, dict) or model.get('record_type') != 'potential_model_card':
                        errors.append('model_card reference is not a potential_model_card')
                    else:
                        actual = record.get('potential_identity')
                        expected = model.get('identity', {})
                        if isinstance(actual, dict):
                            for key in ('sha256', 'bytes'):
                                if actual.get(key) is None or expected.get(key) is None:
                                    unknown.append('Missing comparable potential identity: ' + key)
                                elif actual[key] != expected[key]:
                                    errors.append('Attempt/model identity mismatch: ' + key)
                        else:
                            unknown.append('Attempt potential identity is unresolved')
                        for key in ('precision', 'interface_revision'):
                            expected_value = model.get('interface', {}).get('revision' if key == 'interface_revision' else key)
                            if expected_value is not None and record.get(key) is not None:
                                if expected_value != record[key]:
                                    errors.append('Attempt/model interface mismatch: ' + key)
                            else:
                                unknown.append('No comparable interface declaration: ' + key)
                except (ValueError, OSError, AttributeError) as error:
                    errors.append('Cannot inspect model reference: ' + str(error))
            else:
                unknown.append('No available model_card for attempt comparison')
            if record.get('parent_attempt'):
                restart = record.get('parent_restart_identity')
                if isinstance(restart, dict):
                    check_identity(restart)
                else:
                    unknown.append('Restart source identity is unresolved')
                unknown.append('Restart engine/state compatibility requires separate evidence')
            evidence_ref = record.get('compatibility_evidence')
            if isinstance(evidence_ref, str):
                try:
                    evidence_path = base / evidence_ref
                    evidence = read_record(evidence_path)
                    if not isinstance(evidence, dict):
                        raise ValueError('Compatibility evidence must be an object')
                    for key in ('executable', 'interface_revision', 'precision'):
                        if record.get(key) is None or evidence.get(key) is None:
                            unknown.append('Incomplete compatibility identity: ' + key)
                        elif record[key] != evidence[key]:
                            errors.append('Compatibility evidence mismatch: ' + key)
                    actual = record.get('potential_identity')
                    if not isinstance(actual, dict) or not actual.get('sha256'):
                        unknown.append('No attempt potential hash for compatibility evidence')
                    elif evidence.get('potential_sha256') != actual['sha256']:
                        errors.append('Compatibility evidence potential mismatch')
                    scenario = record.get('validation_scenario')
                    if not scenario or not evidence.get('scenario'):
                        unknown.append('Compatibility scenario unresolved')
                    elif evidence['scenario'] != scenario:
                        errors.append('Compatibility evidence scenario mismatch')
                    if evidence.get('status') != 'PASSED':
                        unknown.append('Compatibility evidence is not a passed validation')
                    raw = evidence.get('raw_evidence')
                    if not isinstance(raw, list) or not raw:
                        unknown.append('No raw evidence references for compatibility validation')
                    else:
                        for item in raw:
                            if not isinstance(item, str) or not (evidence_path.parent / item).is_file():
                                errors.append('Missing raw compatibility evidence: ' + str(item))
                    unknown.append('Raw validation contents and acceptance thresholds require domain-specific assessment')
                except (ValueError, OSError) as error:
                    errors.append('Cannot read compatibility evidence: ' + str(error))
        unknown.append('Engine compatibility requires scenario-specific validation evidence; declarations alone are insufficient')
    return {'status': 'INCONSISTENT' if errors else 'PARTIAL' if unknown else 'CHECKED',
            'errors': errors, 'unknown': unknown,
            'scope': 'Explicit local references, file identities and declared mappings only'}


def validate_record(record, kind=None):
    from jsonschema import Draft202012Validator
    kind = kind or KINDS.get(record.get('record_type'))
    if kind not in {*KINDS.values(), 'package-manifest'}:
        raise ValueError('Unknown record type; select an explicit supported kind.')
    schema = json.loads((SCHEMAS / (kind + '.schema.json')).read_text(encoding='utf-8'))
    errors = [{'path': list(error.absolute_path), 'message': error.message}
              for error in Draft202012Validator(schema).iter_errors(record)]
    return {'status': 'INVALID' if errors else 'STRUCTURALLY_VALID', 'kind': kind,
            'errors': errors, 'scope': 'Structural schema only; no cross-file, scientific or authorization acceptance.',
            'execution_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--kind', choices=[*KINDS.values(), 'package-manifest'])
    parser.add_argument('--check-links', action='store_true')
    parser.add_argument('--reference-root', type=Path,
                        help='Explicit reference base; default is the record directory.')
    args = parser.parse_args()
    try:
        record = read_record(args.record)
        if not isinstance(record, dict):
            raise ValueError('Record must be a JSON object.')
        report = validate_record(record, args.kind)
        if args.check_links and not report['errors']:
            report['links'] = validate_links(record, args.reference_root or args.record.resolve().parent)
            if report['links']['errors']:
                report['status'] = 'INVALID'
    except (ValueError, OSError, ImportError, TypeError, KeyError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'execution_performed': False}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['status'] == 'INVALID' else 0


if __name__ == '__main__':
    sys.exit(main())
