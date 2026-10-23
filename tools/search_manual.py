"""Literal search of an explicitly selected, release-matched offline RST manual."""
import argparse
from pathlib import Path


def search(folder, query, limit):
    if not query.strip() or limit < 1:
        raise ValueError('Use a nonempty query and a positive limit.')
    folder = Path(folder).expanduser().resolve(strict=True)
    pages = list(folder.glob('*.rst'))
    if not pages:
        raise ValueError('Selected folder has no top-level RST pages; choose the release doc/src directory.')
    pages.sort(key=lambda path: (query.casefold() not in path.stem.casefold(), path.name))
    found = []
    for path in pages:
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if query.casefold() in line.casefold():
                found.append((str(path), number, line.strip()))
                if len(found) >= limit:
                    return found
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manual-dir', required=True)
    parser.add_argument('--query', required=True)
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    matches = search(args.manual_dir, args.query, args.limit)
    for path, line, text in matches:
        print(f'{path}:{line}: {text}')
    if not matches:
        print('No literal match in the selected manual; not evidence that a feature is unsupported.')


if __name__ == '__main__':
    main()
