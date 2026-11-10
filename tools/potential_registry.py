"""Read-only empirical/pretrained potential discovery, not automatic selection."""
import math
import json
from pathlib import Path


def load_index(path):
    from jsonschema import Draft202012Validator
    schema_path = Path(__file__).resolve().parents[1] / 'schemas/potential-index.schema.json'
    record = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    Draft202012Validator(json.loads(schema_path.read_text())).validate(record)
    search(record['entries'])  # Enforce unique IDs before any selection.
    return record


def search(entries, elements=(), kind=None, maximum_energy_mae=None, dataset=None, scenario=None):
    if maximum_energy_mae is not None and (not math.isfinite(maximum_energy_mae) or maximum_energy_mae < 0):
        raise ValueError('Energy MAE threshold must be finite and nonnegative')
    if maximum_energy_mae is not None and (not dataset or not scenario):
        raise ValueError('Accuracy filtering requires an explicit dataset and scenario')
    results = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Potential entries must be objects')
        identifier = entry.get('id')
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError('Potential IDs must be nonempty and unique')
        seen.add(identifier)
        if kind is not None and entry.get('kind') != kind:
            continue
        if not set(elements).issubset(set(entry.get('elements', []))):
            continue
        metrics = entry.get('metrics', {})
        if not isinstance(metrics, dict):
            raise ValueError('Potential metrics must be an object')
        metric = metrics.get('energy_mae_ev_per_atom')
        if maximum_energy_mae is not None:
            context = entry.get('metric_context', {})
            if not isinstance(context, dict):
                raise ValueError('Metric context must be an object')
            if context.get('dataset') != dataset or context.get('scenario') != scenario or not context.get('evidence'):
                continue
            if not isinstance(metric, (int, float)) or isinstance(metric, bool) or not math.isfinite(metric):
                continue
            if metric < 0:
                raise ValueError('Reported energy MAE cannot be negative')
            if metric > maximum_energy_mae:
                continue
        results.append(dict(entry))
    return results
