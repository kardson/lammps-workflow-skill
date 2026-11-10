"""Query scoped validation evidence; never promote missing evidence to support."""
import json
from pathlib import Path
DIMENSIONS = ('installation', 'numerical', 'mpi', 'deposition', 'restart', 'physical_accuracy')


def load_evidence(path):
    path = Path(path).resolve()
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(document, dict) or document.get('schema_version') != 1 or not isinstance(document.get('records'), list):
        raise ValueError('Expected v1 compatibility evidence records')
    records = []
    for record in document['records']:
        if not isinstance(record, dict) or not all(isinstance(record.get(key), str) and record[key]
                for key in ('model_sha256', 'engine_id', 'scenario', 'dimension', 'status')):
            raise ValueError('Malformed compatibility record')
        if record['dimension'] not in DIMENSIONS or record['status'] not in ('PASSED', 'FAILED', 'UNVERIFIED', 'PARTIAL'):
            raise ValueError('Unsupported compatibility dimension/status')
        sources = record.get('evidence')
        if not isinstance(sources, list) or not sources or not all(isinstance(value, str) for value in sources):
            raise ValueError('Compatibility records require evidence path references')
        item = dict(record)
        item['recorded_status'] = record['status']
        item['missing_evidence'] = [value for value in sources if not (path.parent / value).is_file()]
        if item['missing_evidence']:
            item['status'] = 'UNVERIFIED'
        records.append(item)
    return records


def query(records, model_sha256, engine_id, scenario):
    if not all(isinstance(value, str) and value for value in (model_sha256, engine_id, scenario)):
        raise ValueError('Explicit model identity, engine ID and scenario are required')
    selected = [record for record in records if record.get('model_sha256') == model_sha256
                and record.get('engine_id') == engine_id and record.get('scenario') == scenario]
    dimensions = {}
    for name in DIMENSIONS:
        evidence = [record for record in selected if record.get('dimension') == name]
        states = {record.get('status') for record in evidence}
        status = 'UNVERIFIED'
        if 'FAILED' in states:
            status = 'CONFLICTING' if 'PASSED' in states else 'FAILED'
        elif 'PASSED' in states:
            status = 'PASSED_RECORDED'
        dimensions[name] = {'status': status, 'records': evidence}
    return {'model_sha256': model_sha256, 'engine_id': engine_id, 'scenario': scenario,
            'dimensions': dimensions, 'scope': 'Matching recorded evidence only; no runtime observation, evidence authenticity or scientific acceptance.'}
