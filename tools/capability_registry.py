"""Read-only capability lookup; no imports of optional scientific runtimes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lookup(capability_id=None, category=None):
    registry = json.loads((ROOT / 'capabilities.json').read_text(encoding='utf-8'))
    contracts = {item['entrypoint']: item for item in
                 json.loads((ROOT / 'cli-contracts.json').read_text(encoding='utf-8'))['entries']}
    selected = []
    for entry in registry['entries']:
        if capability_id is not None and entry['id'] != capability_id:
            continue
        if category is not None and entry['category'] != category:
            continue
        item = dict(entry)
        item['contract'] = contracts[entry['contract_entrypoint']]
        selected.append(item)
    if capability_id is not None and not selected:
        raise ValueError('Unknown or unmatched capability: ' + capability_id)
    return selected
