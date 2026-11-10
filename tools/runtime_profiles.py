"""Validate local profile references without touching a compute host."""


def check_bindings(profiles, binding):
    ids = [profile.get('id') for profile in profiles]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Engine profile IDs must be nonempty and unique')
    errors = []
    seen = set()
    for item in binding.get('engine_bindings', []):
        identifier = item.get('engine_id')
        if identifier not in ids:
            errors.append('Unknown engine profile: ' + str(identifier))
        if identifier in seen:
            errors.append('Duplicate engine binding: ' + str(identifier))
        seen.add(identifier)
        if not isinstance(item.get('executable'), str) or not item['executable']:
            errors.append('Missing executable binding: ' + str(identifier))
    return {'status': 'INVALID' if errors else 'DECLARATIONS_MATCH', 'errors': errors,
            'live_readiness': 'UNVERIFIED', 'scope': 'Local identifiers and path declarations only'}
