"""Audit declared report claims without granting scientific acceptance."""
from pathlib import Path

from local_common import identity


FIELDS = ('attempt', 'method_version', 'time_window', 'atom_selection', 'formula',
          'unit', 'result', 'uncertainty', 'acceptance_conditions', 'limitations')


def audit(config, base):
    if not isinstance(config, dict) or config.get('report_class') not in {'diagnostic', 'engineering', 'research'}:
        raise ValueError('Explicit diagnostic/engineering/research report_class required.')
    claims = config.get('claims')
    if not isinstance(claims, list):
        raise ValueError('claims must be a list.')
    records, ids = [], set()
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get('id'), str) or not claim['id'].strip():
            raise ValueError('Each claim requires a nonempty id.')
        if claim['id'] in ids:
            raise ValueError('Duplicate claim id.')
        ids.add(claim['id'])
        missing = [key for key in FIELDS if claim.get(key) is None or claim.get(key) == ''
                   or claim.get(key) == [] or claim.get(key) == {}]
        if not isinstance(claim.get('statement'), str) or not claim['statement'].strip():
            missing.append('statement')
        sources = claim.get('sources', [])
        if not isinstance(sources, list):
            raise ValueError('sources must be a list.')
        checked = []
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get('path'), str):
                raise ValueError('Each source requires a path.')
            entry = dict(source)
            try:
                path = Path(source['path'])
                actual = identity(path if path.is_absolute() else Path(base) / path)
                entry['observed_identity'] = actual
                entry['status'] = 'IDENTITY_MATCH' if source.get('sha256') == actual['sha256'] else 'HASH_UNRESOLVED_OR_MISMATCH'
            except (OSError, ValueError) as error:
                entry['status'] = 'UNAVAILABLE'
                entry['issue'] = str(error)
            if entry['status'] != 'IDENTITY_MATCH' or not source.get('locator'):
                missing.append('source identity/locator')
            checked.append(entry)
        if not checked:
            missing.append('sources')
        record = dict(claim)
        record.update(sources=checked, missing_evidence=sorted(set(missing)),
                      status='PARTIAL' if missing else 'DECLARED_CHAIN_PRESENT')
        records.append(record)
    return {'report_class': config['report_class'], 'claims': records,
            'status': 'PARTIAL' if not records or any(x['missing_evidence'] for x in records) else 'DECLARED_CHAINS_PRESENT',
            'scientific_acceptance': 'UNVERIFIED',
            'limitations': ['Hash and locator presence do not verify a claim or its scientific interpretation.',
                            'Reported result, method, uncertainty and acceptance conditions are declarations.']}
