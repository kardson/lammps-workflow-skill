"""Inspect explicit restart preparation records; never read binary state or launch."""
import hashlib
from pathlib import Path


def inspect(record, base):
    if not isinstance(record, dict):
        raise ValueError('Restart candidate must be an object')
    errors, unresolved = [], []
    for key in ('parent_attempt', 'source_engine_id', 'target_engine_id', 'potential_sha256',
                'phase', 'fix_state_evidence', 'counter_origin', 'compatibility_evidence'):
        if record.get(key) is None:
            unresolved.append(key)
    for key in ('fix_state_evidence', 'compatibility_evidence'):
        value = record.get(key)
        if value is not None and (not isinstance(value, str) or not (Path(base) / value).is_file()):
            errors.append('Missing preparation evidence: ' + key)
    if record.get('source_engine_id') != record.get('target_engine_id'):
        unresolved.append('cross_engine_binary_restart_not_established')
    start, end = record.get('completed_step'), record.get('target_step')
    if type(start) is not int or type(end) is not int:
        unresolved.append('explicit_integer_steps')
    elif start < 0 or end <= start:
        errors.append('Target step must exceed nonnegative completed step')
    checkpoint = record.get('checkpoint', {})
    if not isinstance(checkpoint, dict) or not checkpoint.get('file') or not checkpoint.get('sha256'):
        unresolved.append('checkpoint_identity')
    else:
        if not isinstance(checkpoint['file'], str) or not isinstance(checkpoint['sha256'], str):
            raise ValueError('Checkpoint path and SHA256 must be strings')
        path = Path(base) / checkpoint['file']
        if not path.is_file():
            errors.append('Checkpoint file missing')
        else:
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != checkpoint['sha256']:
                errors.append('Checkpoint identity mismatch')
    return {'status': 'INVALID' if errors else 'PREPARATION_INCOMPLETE' if unresolved else 'DECLARATIONS_COMPLETE',
            'errors': errors, 'unresolved': unresolved, 'engine_state_verified': False,
            'execution_authorized': False, 'scope': 'Local identity and preparation declarations only; no binary compatibility certification.'}
