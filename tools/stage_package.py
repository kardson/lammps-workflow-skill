"""Local receiving-side staging primitive; no network or engine execution."""
import json
from pathlib import Path
import shutil
import uuid
from functools import wraps
from local_common import identity


def reserve_destination(method):
    @wraps(method)
    def guarded(source, destination):
        destination = Path(destination).absolute()
        lock = destination.with_name(destination.name + '.stage-lock')
        try:
            lock.mkdir()
        except FileExistsError:
            raise RuntimeError('Staging destination reserved; reconcile existing transfer before retry')
        try:
            return method(source, destination)
        finally:
            lock.rmdir()
    return guarded


@reserve_destination
def stage(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if destination.exists():
        raise FileExistsError(destination)
    manifest_path = source / 'package-manifest.json'
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    files = manifest['package_files']
    identities = {item['package_file']: item for item in manifest['file_identities']}
    if len(files) != len(set(files)) or len(identities) != len(manifest['file_identities']) or set(files) != set(identities):
        raise ValueError('Package inventory mismatch')
    temporary = destination.with_name(destination.name + '.partial-' + uuid.uuid4().hex)
    temporary.mkdir()
    for name in files:
        relative = Path(name)
        cursor = source
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink() or (hasattr(cursor, 'is_junction') and cursor.is_junction()):
                raise ValueError('Linked package member rejected; partial staging retained')
        original = (source / relative).resolve()
        if relative.is_absolute() or not original.is_relative_to(source) or any(part.startswith('.') for part in relative.parts):
            raise ValueError('Invalid package member; partial staging retained')
        observed = identity(original)
        if any(observed[key] != identities[name][key] for key in ('sha256', 'bytes')):
            raise ValueError('Source identity mismatch; partial staging retained')
        target = temporary / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        copied = identity(target)
        if any(copied[key] != identities[name][key] for key in ('sha256', 'bytes')):
            raise ValueError('Received identity mismatch; partial staging retained')
    (temporary / 'package-manifest.json').write_bytes(raw)
    (temporary / 'stage-receipt.json').write_text(json.dumps({'status': 'INPUT_FILES_VERIFIED',
        'files': files, 'scope': 'Local copy only; no engine, authorization or scientific validation'}, indent=2))
    if destination.exists():
        raise FileExistsError('Destination appeared during staging; partial package retained')
    temporary.rename(destination)
    return destination
