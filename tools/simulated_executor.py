"""File-only execution protocol fixture. Never starts a process or connects."""
import json
import os
from pathlib import Path
import uuid
from functools import wraps


def exclusive(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        lock = self.directory / '.mutation-lock'
        try:
            lock.mkdir()
        except FileExistsError:
            raise RuntimeError('Attempt mutation locked; reconcile interrupted/concurrent request before retry')
        try:
            return method(self, *args, **kwargs)
        finally:
            lock.rmdir()
    return guarded


class SimulatedExecutor:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _save(self, record):
        temporary = self.directory / ('state-' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, self.directory / 'state.json')

    @exclusive
    def prepare(self, attempt_id):
        if (self.directory / 'state.json').exists():
            raise FileExistsError('Attempt state already exists')
        record = {'attempt_id': attempt_id, 'execution_state': 'PREPARED',
                  'observation': 'SIMULATED', 'launch_requests': 0, 'events': ['PREPARED'],
                  'scope': 'File-only fixture; no process or MD exists'}
        self._save(record)
        return record

    def status(self):
        return json.loads((self.directory / 'state.json').read_text(encoding='utf-8'))

    @exclusive
    def stage(self):
        record = self.status()
        if record['execution_state'] != 'PREPARED':
            raise ValueError('Only a prepared attempt can be staged')
        record['execution_state'] = 'STAGED'
        record['events'].append('STAGED')
        self._save(record)

    @exclusive
    def launch(self):
        record = self.status()
        if record['observation'] == 'UNKNOWN':
            raise ValueError('Unknown observation must be reconciled before launch requests')
        if record['execution_state'] in ('RUNNING', 'SUCCEEDED', 'FAILED'):
            return record
        if record['execution_state'] != 'STAGED':
            raise ValueError('Cannot launch unstaged attempt')
        record['execution_state'] = 'RUNNING'
        record['launch_requests'] += 1
        record['events'].append('SIMULATED_LAUNCH')
        self._save(record)
        return record

    @exclusive
    def observe(self, available=True):
        record = self.status()
        record['observation'] = 'SIMULATED' if available else 'UNKNOWN'
        record['events'].append('OBSERVATION_' + record['observation'])
        self._save(record)
        return record

    @exclusive
    def collect(self, required, available):
        record = self.status()
        if record['execution_state'] not in ('SUCCEEDED', 'FAILED'):
            raise ValueError('Fixture collection requires terminal execution state')
        record['collection'] = {'collected': [name for name in required if name in available],
                                'missing': [name for name in required if name not in available]}
        record['collection']['status'] = 'PARTIAL' if record['collection']['missing'] else 'COMPLETE'
        record['events'].append('COLLECTION_' + record['collection']['status'])
        self._save(record)
        return record

    @exclusive
    def finish(self, exit_code):
        record = self.status()
        if record['execution_state'] != 'RUNNING':
            raise ValueError('Only running fixture can finish')
        record['execution_state'] = 'SUCCEEDED' if exit_code == 0 else 'FAILED'
        record['exit_code'] = exit_code
        record['events'].append(record['execution_state'])
        self._save(record)
        return record
