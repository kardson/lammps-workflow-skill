"""Shared helpers for small, non-executing workflow tools."""
from datetime import datetime, timezone
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def evidence_path(value):
    path = Path(value).expanduser().resolve()
    if path.is_relative_to(SKILL_ROOT):
        raise ValueError('Write research evidence outside the installed skill directory.')
    if path.exists():
        raise FileExistsError('Existing evidence preserved; select a new output path.')
    return path


def write_report(path, report):
    path = evidence_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def print_receipt(path, **fields):
    print(json.dumps({'report': str(path), **fields}, ensure_ascii=False))
