"""Archive only explicitly registered input files after identity verification."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

from common import evidence_path, print_receipt, utc_now, write_report
from local_common import identity


def bundle(directory, archive, receipt):
    root = Path(directory).resolve(strict=True)
    manifest_path = root / 'package-manifest.json'
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw.decode('utf-8'))
    if manifest['status'] != 'PREPARED_CANDIDATE_NOT_ENGINE_VALIDATED':
        raise ValueError('Unsupported package status; no archive created.')
    archive, receipt = evidence_path(archive), evidence_path(receipt)
    if archive == receipt:
        raise ValueError('Archive and receipt paths must differ.')
    files = manifest['package_files']
    expected = {item['package_file']: item for item in manifest['file_identities']}
    if len(files) != len(set(files)) or set(files) != set(expected):
        raise ValueError('Package file list and identity inventory disagree.')
    verified = []
    for name in files:
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe archive member path.')
        if any(part.startswith('.') or part in {'.ssh', '.aws'} for part in relative.parts):
            raise ValueError('Hidden/configuration files are outside the package contract.')
        path = root / Path(*relative.parts)
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Package member resolves outside its root.')
        observed = identity(path)
        if (observed['sha256'], observed['bytes']) != (expected[name]['sha256'], expected[name]['bytes']):
            raise ValueError('Package member changed after preparation: ' + name)
        verified.append({'package_file': name, **observed})
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as output:
        for item in verified:
            output.write(root / item['package_file'], arcname=item['package_file'])
        output.writestr('package-manifest.json', manifest_raw)
    with zipfile.ZipFile(archive) as check:
        if check.testzip() is not None:
            raise ValueError('Archive CRC verification failed; archive preserved for diagnosis.')
        for item in verified:
            digest = hashlib.sha256()
            count = 0
            with check.open(item['package_file']) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
                    count += len(block)
            if digest.hexdigest() != item['sha256'] or count != item['bytes']:
                raise ValueError('Archived file differs from the verified package; archive preserved for diagnosis.')
    report = {'bundled_utc': utc_now(), 'archive': identity(archive),
              'source_manifest': {'path': str(manifest_path), 'bytes': len(manifest_raw), 'sha256': hashlib.sha256(manifest_raw).hexdigest()},
              'verified_files': verified, 'archive_members': [*files, 'package-manifest.json'],
              'archive_crc_verified': True, 'transferred': False, 'execution_authorized': False,
              'scope': 'Local packaging of exact candidate inputs only; does not establish target-runtime or scientific acceptance.'}
    write_report(receipt, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-directory', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    result = bundle(args.package_directory, args.archive, args.receipt)
    print_receipt(args.receipt, archive_bytes=result['archive']['bytes'], transferred=False)


if __name__ == '__main__':
    main()
