"""Evaluate explicit local blockers without inferring scientific approval."""


def stage_blockers(record, stage):
    if not isinstance(record, dict) or not isinstance(record.get('entries'), list):
        raise ValueError('Decision log requires an entries array')
    blockers = []
    for entry in record.get('entries', []):
        if not isinstance(entry, dict) or not all(key in entry for key in ('id', 'status', 'summary', 'blocks')):
            raise ValueError('Malformed decision entry; validate the decision-log schema first')
        if not isinstance(entry['blocks'], list):
            raise ValueError('Decision blocks must be an array')
        if entry.get('status') not in ('RESOLVED', 'SUPERSEDED') and stage in entry.get('blocks', []):
            blockers.append({'id': entry['id'], 'reason': entry['summary'],
                             'release_condition': entry.get('release_condition')})
    return blockers
