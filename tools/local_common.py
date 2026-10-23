"""File/config helpers for local preparation; no simulation launcher."""
import hashlib
import json
import math
from pathlib import Path

from common import evidence_path


def load_config(path):
    path = Path(path).expanduser().resolve(strict=True)
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a JSON object.')
    return config, path.parent


def resolve_file(value, base):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('An explicit source filename is required.')
    path = Path(value).expanduser()
    return (path if path.is_absolute() else Path(base) / path).resolve(strict=True)


def identity(path):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed during identity check: ' + str(path))
    return {'path': str(path), 'bytes': after.st_size, 'sha256': digest.hexdigest()}


def new_directory(value):
    path = evidence_path(value)
    path.mkdir(parents=True, exist_ok=False)
    return path


def number(value, name, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be an explicit finite number.')
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(name + ' is outside its allowed range.')
    return value


def integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(name + ' must be an integer >= ' + str(minimum))
    return value


def require(config, keys):
    missing = [key for key in keys if config.get(key) is None]
    if missing:
        raise ValueError('Unresolved required configuration fields: ' + ', '.join(missing))


def json_file(path, record):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
