"""Select explicit version-bound references; no latest-version fallback."""


def select(entries, engine_id, topic):
    return [dict(entry) for entry in entries
            if engine_id in entry.get('engine_ids', []) and topic in entry.get('topics', [])]
