"""Shared v1 record reading; no scientific defaults or execution."""
import json
from pathlib import Path


def read_record(path):
    path = Path(path).resolve()
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(record, dict):
        raise ValueError('Record must be a JSON object.')
    version = record.get('schema_version')
    if version is not None and (type(version) is not int or version != 1):
        raise ValueError('Unsupported schema_version; preserve source and use an explicit migration.')
    return record


def reference_path(record_path, reference, root=None):
    if not isinstance(reference, str) or not reference:
        raise ValueError('Reference must be a nonempty path string.')
    base = Path(root).resolve() if root is not None else Path(record_path).resolve().parent
    return (base / reference).resolve()


def copy_record(source, destination):
    """Validated v1 byte-preserving copy, refusing replacement; not a version upgrade."""
    source, destination = Path(source), Path(destination)
    record = read_record(source)
    if record.get('schema_version') != 1:
        raise ValueError('Copy requires an explicit supported v1 record.')
    with destination.open('xb') as stream:
        stream.write(source.read_bytes())
