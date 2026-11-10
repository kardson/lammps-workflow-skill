"""Read-only source binding checks for declared stages; no live host certification."""
import hashlib
import json
from pathlib import Path

from compatibility_registry import DIMENSIONS, load_evidence, query
from stage_contract import SUPPORT_FIELDS


def check(contract, reference_root):
    root = Path(reference_root).resolve(strict=True)
    errors, unknown, stages = [], [], []
    def bound_file(path_value, digest):
        if not isinstance(path_value, str) or not path_value or not isinstance(digest, str) or not digest:
            raise ValueError('Explicit file path and hash required')
        path = Path(path_value)
        if path.is_absolute() or '\\' in path_value or ':' in path_value or '..' in path.parts:
            raise ValueError('Portable project-relative reference required')
        path = (root / path).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError('Reference outside project or exceeds 4 MiB bound')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Referenced identity mismatch: ' + path_value)
        return path, json.loads(raw.decode('utf-8-sig'))
    binding = contract.get('plan_binding') or {}
    try:
        _, plan = bound_file(binding.get('file'), binding.get('sha256'))
        if not isinstance(plan, dict) or plan.get('schema_version') != 1 or plan.get('record_type') != 'md_plan' or plan.get('id') != binding.get('id'):
            errors.append('Plan record identity/type/version mismatch')
    except (OSError, ValueError) as error:
        if not all(binding.get(key) for key in ('id', 'file', 'sha256')):
            unknown.append('Plan source unresolved')
        else:
            errors.append(str(error))
    for stage in contract.get('stages', []):
        support = stage.get('engine_support') or {}
        item = {'id': stage.get('id'), 'status': 'UNVERIFIED'}
        stages.append(item)
        required = SUPPORT_FIELDS
        if not isinstance(support, dict) or any(not isinstance(support.get(key), str) or not support[key] for key in required):
            unknown.append(str(stage.get('id')) + ': engine/scenario binding unresolved')
            continue
        required_dimensions = support.get('required_dimensions')
        if not isinstance(required_dimensions, list) or not required_dimensions or any(not isinstance(name, str) or name not in DIMENSIONS for name in required_dimensions):
            unknown.append(str(stage.get('id')) + ': required evidence dimensions unresolved')
            continue
        try:
            _, profiles = bound_file(support['profile_file'], support['profile_sha256'])
            profiles = profiles.get('profiles', [profiles])
            matches = [profile for profile in profiles if isinstance(profile, dict) and profile.get('id') == support['engine_id']]
            if len(matches) != 1 or matches[0].get('schema_version') != 1 or matches[0].get('record_type') != 'engine_profile':
                raise ValueError('Selected engine profile missing/ambiguous/unsupported')
            evidence_path, _ = bound_file(support['evidence_file'], support['evidence_sha256'])
            result = query(load_evidence(evidence_path), support['model_sha256'], support['engine_id'], support['scenario'])
            item['recorded_evidence'] = result
            states = [dimension['status'] for dimension in result['dimensions'].values()]
            if any(state in ('FAILED', 'CONFLICTING') for state in states):
                item['status'] = 'FAILED_OR_CONFLICTING_RECORDED'
                errors.append(str(stage['id']) + ': matching failure/conflicting evidence')
            elif all(result['dimensions'][name]['status'] == 'PASSED_RECORDED' for name in required_dimensions):
                item['status'] = 'MATCHING_RECORDED_EVIDENCE'
            else:
                unknown.append(str(stage['id']) + ': no matching passing recorded scenario')
        except (OSError, ValueError, TypeError, AttributeError) as error:
            errors.append(str(stage.get('id')) + ': ' + str(error))
    return {'status': 'INCONSISTENT' if errors else 'PARTIAL' if unknown else 'LINKS_MATCH_RECORDED_EVIDENCE',
            'errors': errors, 'unresolved': unknown, 'stages': stages,
            'scope': 'Exact local source/scenario linkage only; no current host readiness or stage physics certification'}
