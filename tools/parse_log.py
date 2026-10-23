"""Stream conventional single-line LAMMPS thermo blocks into bounded summaries."""
import argparse
import hashlib
import math
from pathlib import Path
import re

from common import evidence_path, print_receipt, utc_now, write_report

NUMBER = re.compile(r'^[+-]?(?:(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?|inf(?:inity)?|nan)$', re.I)
HEADER = re.compile(r'^[A-Za-z_][A-Za-z0-9_\[\]/.:-]*$')


def parse_log(path):
    path = Path(path).expanduser().resolve(strict=True)
    before = path.stat()
    digest = hashlib.sha256()
    blocks, errors, warnings, issues, loops = [], [], [], [], []
    active, pending_header, yaml_active, unsupported_formats = None, None, False, set()
    nonfinite_count, error_count, warning_count, issue_count = 0, 0, 0, 0

    def issue(line, reason):
        nonlocal issue_count
        issue_count += 1
        if len(issues) < 100:
            issues.append({'line': line, 'reason': reason})

    def finish():
        nonlocal active
        if active is not None:
            blocks.append(active)
            active = None

    with path.open('rb') as stream:
        for line_number, raw in enumerate(stream, 1):
            digest.update(raw)
            decoded = raw.decode('utf-8', errors='replace')
            if '\ufffd' in decoded:
                issue(line_number, 'Invalid UTF-8 replaced; inspect original bytes.')
            text = decoded.strip()
            if text.startswith('ERROR:') or re.match(r'^ERROR on proc\b', text):
                error_count += 1
                if len(errors) < 100:
                    errors.append({'line': line_number, 'text': text[:2000]})
                finish()
                pending_header = None
                continue
            if text.startswith('WARNING:'):
                warning_count += 1
                if len(warnings) < 100:
                    warnings.append({'line': line_number, 'text': text[:2000]})
                continue  # A warning can interrupt a still-active thermo block.
            if text.startswith('Loop time of '):
                if active is not None:
                    active['following_loop_line'] = line_number
                finish()
                pending_header = None
                if len(loops) < 100:
                    loops.append({'line': line_number, 'text': text[:2000]})
                continue
            if text.startswith('keywords:') or text == 'data:':
                finish()
                pending_header = None
                yaml_active = True
                unsupported_formats.add('YAML thermo')
                continue
            if text == '...':
                yaml_active = False
                continue
            if yaml_active:
                continue
            if re.match(r'^-+\s*Step\s+\d+\s+-+', text):
                finish()
                pending_header = None
                unsupported_formats.add('multi-line thermo')
                continue
            words = text.split()
            # A one-line header is promoted only after a numeric row follows it.
            candidate = (len(words) >= 2 and ('Step' in words or 'Time' in words) and
                         len(set(words)) == len(words) and
                         all(HEADER.fullmatch(word) for word in words))
            if candidate:
                finish()
                pending_header = (line_number, words)
                continue
            numeric = bool(words) and all(NUMBER.fullmatch(word) for word in words)
            if pending_header and numeric:
                header_line, columns = pending_header
                active = {'header_line': header_line, 'columns': columns, 'row_count': 0,
                          'first': None, 'last': None, 'min': {}, 'max': {},
                          'nonfinite_values': 0, 'following_loop_line': None}
                pending_header = None
            if active is not None and numeric:
                if len(words) != len(active['columns']):
                    issue(line_number, 'Numeric row width differs from thermo header.')
                    finish()
                    continue
                values = [int(word) if re.fullmatch(r'[+-]?\d+', word) else
                          float(word.replace('D', 'E').replace('d', 'e')) for word in words]
                safe_values = [value if math.isfinite(value) else None for value in values]
                record = dict(zip(active['columns'], safe_values))
                if active['row_count'] == 0:
                    active['first'] = {'line': line_number, 'values': record}
                active['last'] = {'line': line_number, 'values': record}
                active['row_count'] += 1
                for column, value in zip(active['columns'], values):
                    if not math.isfinite(value):
                        nonfinite_count += 1
                        active['nonfinite_values'] += 1
                    else:
                        active['min'][column] = min(active['min'].get(column, value), value)
                        active['max'][column] = max(active['max'].get(column, value), value)
                continue
            if (active is not None or pending_header) and words and NUMBER.fullmatch(words[0]):
                issue(line_number, 'Partially numeric row not parsed; possible truncated/malformed output.')
            if text:
                finish()
                pending_header = None
    if pending_header:
        issue(pending_header[0], 'Thermo header has no following numeric row at end of file.')
    finish()
    after = path.stat()
    source_changed = (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
    scope = 'PARTIAL' if unsupported_formats or source_changed or issue_count else ('PARSED_SINGLE_LINE_THERMO' if blocks else 'NO_SUPPORTED_THERMO')
    return {'observed_utc': utc_now(), 'log': str(path), 'source_bytes_before': before.st_size,
            'source_bytes_after': after.st_size, 'observed_stream_sha256': digest.hexdigest(),
            'source_changed_during_read': source_changed, 'parse_scope': scope,
            'thermo_blocks': blocks, 'error_count': error_count, 'errors_first_100': errors,
            'warning_count': warning_count, 'warnings_first_100': warnings,
            'nonfinite_values': nonfinite_count, 'loop_lines_first_100': loops,
            'issue_count': issue_count, 'issues_first_100': issues,
            'unsupported_formats': sorted(unsupported_formats),
            'job_state': 'UNVERIFIED', 'numerical_acceptance': 'UNVERIFIED', 'scientific_acceptance': 'UNVERIFIED',
            'simulation_run': False,
            'limitations': ['Single-line tabular thermo with a Step or Time header only; no multi/YAML parser, MPI partition separation or arbitrary format inference.',
                            'Log errors and loop markers are observations, not process exit evidence or proof that the whole job finished.',
                            'Blocks remain separate, including reset steps; no guessed timestep, units, production window or equilibrium.',
                            'No trajectory, atom balance, uncertainty or potential-accuracy validation.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = evidence_path(args.output)
    report = parse_log(args.log)
    write_report(output, report)
    print_receipt(output, parse_scope=report['parse_scope'], thermo_blocks=len(report['thermo_blocks']),
                  error_count=report['error_count'], nonfinite_values=report['nonfinite_values'], job_state='UNVERIFIED')
    if report['error_count'] or report['nonfinite_values'] or report['issue_count'] or report['source_changed_during_read']:
        raise SystemExit(1)
    if report['unsupported_formats'] or not report['thermo_blocks']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
