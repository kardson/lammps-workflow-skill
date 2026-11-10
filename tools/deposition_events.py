"""Stream declared incident-particle events into a bounded-cache SQLite ledger."""
import csv
from contextlib import closing
import math
from pathlib import Path
import re
import sqlite3

from common import utc_now
from local_common import identity, json_file, new_directory, number

EVENTS = ('ATTEMPT', 'REJECTED', 'INSERTED', 'REFLECTED', 'ESCAPED', 'REMOVED_UNKNOWN',
          'COHORT_RETAINED', 'COHORT_NOT_RETAINED')


def apply_event(connection, row, observation_time):
    event, attempt, symbol = row['event'], row['attempt_id'], row['element']
    if event == 'ATTEMPT':
        if row['atom_id']:
            raise ValueError('An insertion attempt is not an admitted atom')
        connection.execute('INSERT INTO attempts VALUES (?,?,?,NULL)', (attempt, symbol, 'PENDING'))
        return
    saved = connection.execute('SELECT element,state,atom_id FROM attempts WHERE id=?', (attempt,)).fetchone()
    if saved is None or saved[0] != symbol:
        raise ValueError('Event has no matching attempt/species')
    if event == 'REJECTED':
        if saved[1] != 'PENDING' or row['atom_id']:
            raise ValueError('Only an unresolved attempt can be rejected')
        connection.execute('UPDATE attempts SET state=? WHERE id=?', ('REJECTED', attempt))
        return
    text = row['atom_id']
    if not text.isdecimal() or not 0 < int(text) <= 9223372036854775807:
        raise ValueError('Positive bounded integer atom ID required')
    atom_id = int(text)
    if event == 'INSERTED':
        if saved[1] != 'PENDING':
            raise ValueError('Attempt already resolved; no duplicate insertion')
        connection.execute('INSERT INTO atoms VALUES (?,?,?,?,?,?)',
                           (atom_id, attempt, symbol, 'IN_BOX', 0, 'UNCLASSIFIED'))
        connection.execute('UPDATE attempts SET state=?,atom_id=? WHERE id=?', ('INSERTED', atom_id, attempt))
        return
    atom = connection.execute('SELECT attempt_id,element,state,reflections,cohort FROM atoms WHERE id=?', (atom_id,)).fetchone()
    if atom is None or atom[0] != attempt or atom[1] != symbol:
        raise ValueError('Atom ID does not belong to the declared incident attempt')
    if atom[2] != 'IN_BOX' or atom[4] != 'UNCLASSIFIED':
        raise ValueError('Event after removal/final cohort observation; explicit reconciliation required')
    if event == 'REFLECTED':
        connection.execute('UPDATE atoms SET reflections=reflections+1 WHERE id=?', (atom_id,))
    elif event in ('ESCAPED', 'REMOVED_UNKNOWN'):
        connection.execute('UPDATE atoms SET state=? WHERE id=?', (event, atom_id))
    elif event in ('COHORT_RETAINED', 'COHORT_NOT_RETAINED'):
        if float(row['time_ps']) != observation_time:
            raise ValueError('Final cohort membership requires the declared observation time')
        connection.execute('UPDATE atoms SET cohort=? WHERE id=?',
                           ('RETAINED' if event == 'COHORT_RETAINED' else 'NOT_RETAINED', atom_id))


def analyze(source, config, output):
    if config.get('source_class') not in ('engineering_fixture', 'upstream_reference', 'research_output'):
        raise ValueError('Explicit event source_class required')
    for key in ('scope_id', 'cohort_definition', 'counter_provenance'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError('Explicit ' + key + ' required')
    elements = config.get('elements')
    if not isinstance(elements, list) or not elements or any(not isinstance(value, str) or not re.fullmatch('[A-Z][a-z]?', value) for value in elements) or len(set(elements)) != len(elements):
        raise ValueError('Explicit unique incident element list required')
    definitions = config.get('event_definitions')
    if not isinstance(definitions, dict) or any(not isinstance(definitions.get(event), str) or not definitions[event].strip() for event in EVENTS):
        raise ValueError('Every supported event requires an explicit method/source definition')
    start = number(config.get('start_time_ps'), 'start_time_ps')
    end = number(config.get('observation_time_ps'), 'observation_time_ps')
    if end < start:
        raise ValueError('Observation time precedes event window')
    source_before = identity(source)
    directory = new_directory(output)
    with closing(sqlite3.connect(directory / 'events.sqlite')) as connection:
        connection.execute('PRAGMA cache_size=-2048')
        connection.execute('PRAGMA temp_store=FILE')
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript('''CREATE TABLE attempts(id TEXT PRIMARY KEY,element TEXT NOT NULL,state TEXT NOT NULL,atom_id INTEGER);
            CREATE TABLE atoms(id INTEGER PRIMARY KEY,attempt_id TEXT UNIQUE NOT NULL REFERENCES attempts(id),element TEXT NOT NULL,state TEXT NOT NULL,reflections INTEGER NOT NULL,cohort TEXT NOT NULL);
            CREATE TABLE events(id TEXT PRIMARY KEY,source_row INTEGER NOT NULL,time_ps REAL NOT NULL,event TEXT NOT NULL,attempt_id TEXT NOT NULL,atom_id TEXT,element TEXT NOT NULL,source TEXT NOT NULL);
            CREATE INDEX atom_element ON atoms(element); CREATE INDEX attempt_element ON attempts(element);''')
        processed, previous_time, failure, source_after = 0, start, None, None
        connection.execute('BEGIN')
        try:
            with open(source, encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                fields = ('event_id', 'time_ps', 'event', 'attempt_id', 'atom_id', 'element', 'source')
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or any(name not in reader.fieldnames for name in fields):
                    raise ValueError('Unique explicit event CSV fields required')
                for index, row in enumerate(reader, 2):
                    if None in row or any(not isinstance(row.get(key), str) for key in fields):
                        raise ValueError('Malformed event CSV row')
                    if not row['event_id'].strip() or not row['attempt_id'].strip() or not row['source'].strip():
                        raise ValueError('Event/attempt/source identity cannot be blank')
                    time = number(float(row['time_ps']), 'event time')
                    if time < previous_time or not start <= time <= end:
                        raise ValueError('Event times must be ordered within the explicit window')
                    if row['element'] not in elements or row['event'] not in EVENTS:
                        raise ValueError('Unknown incident element/event; no inferred classification')
                    connection.execute('SAVEPOINT event_row')
                    try:
                        apply_event(connection, row, end)
                        connection.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',
                            (row['event_id'], index, time, row['event'], row['attempt_id'], row['atom_id'], row['element'], row['source']))
                        connection.execute('RELEASE event_row')
                    except Exception:
                        connection.execute('ROLLBACK TO event_row')
                        connection.execute('RELEASE event_row')
                        raise
                    processed += 1
                    previous_time = time
                    if processed % 1000 == 0:
                        connection.commit()
                        connection.execute('BEGIN')
            if not processed:
                raise ValueError('No incident events supplied')
            source_after = identity(source)
            if source_before != source_after:
                raise ValueError('Event source changed during analysis')
        except (OSError, ValueError, csv.Error, sqlite3.Error) as error:
            failure = {'type': type(error).__name__, 'message': str(error), 'completed_events': processed}
        connection.commit()
        summaries = {}
        for symbol in elements:
            def scalar(sql, parameters):
                return connection.execute(sql, parameters).fetchone()[0]
            attempts = scalar('SELECT count(*) FROM attempts WHERE element=?', (symbol,))
            inserted = scalar("SELECT count(*) FROM attempts WHERE element=? AND state='INSERTED'", (symbol,))
            values = {'attempts': attempts, 'successfully_inserted': inserted,
                      'rejected_attempts': scalar("SELECT count(*) FROM attempts WHERE element=? AND state='REJECTED'", (symbol,)),
                      'pending_attempts': scalar("SELECT count(*) FROM attempts WHERE element=? AND state='PENDING'", (symbol,)),
                      'reflection_events': scalar('SELECT coalesce(sum(reflections),0) FROM atoms WHERE element=?', (symbol,)),
                      'reflected_unique_atoms': scalar('SELECT count(*) FROM atoms WHERE element=? AND reflections>0', (symbol,))}
            for label, predicate in [('escaped', "state='ESCAPED'"), ('removed_unknown', "state='REMOVED_UNKNOWN'"),
                ('retained_at_observation', "state='IN_BOX' AND cohort='RETAINED'"),
                ('not_retained_at_observation', "state='IN_BOX' AND cohort='NOT_RETAINED'"),
                ('unclassified_inserted', "state='IN_BOX' AND cohort='UNCLASSIFIED'")]:
                values[label] = scalar('SELECT count(*) FROM atoms WHERE element=? AND ' + predicate, (symbol,))
            complete_fates = not values['unclassified_inserted'] and not values['removed_unknown']
            values['retained_per_successful_insertion'] = values['retained_at_observation'] / inserted if inserted and complete_fates else None
            summaries[symbol] = values
        with (directory / 'cohort.csv').open('x', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['atom_id', 'attempt_id', 'element', 'state', 'reflection_events', 'cohort'])
            writer.writerows(connection.execute('SELECT * FROM atoms ORDER BY id'))
        with (directory / 'attempts.csv').open('x', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['attempt_id', 'element', 'state', 'atom_id'])
            writer.writerows(connection.execute('SELECT * FROM attempts ORDER BY id'))
    partial = any(values['pending_attempts'] or values['unclassified_inserted'] or values['removed_unknown'] for values in summaries.values())
    report = {'analyzed_utc': utc_now(), 'status': 'FAILED' if failure else 'EVENT_LEDGER_PARTIAL' if partial else 'DECLARED_EVENT_LEDGER_SUMMARY',
        'configuration': config, 'source_before': source_before, 'source_after': source_after, 'events_processed': processed,
        'failure': failure, 'elements': summaries,
        'outputs': [identity(directory / name) for name in ('events.sqlite', 'cohort.csv', 'attempts.csv')],
        'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False,
        'limitations': ['Event/source classifications are supplied, not inferred or authenticated from trajectories',
            'Reflection is crossing history and may overlap retained/escaped outcomes; it is not an exclusive fate',
            'Retained means the declared cohort/selection at the exact supplied time, not bonding or incorporation',
            'No atom ID reuse across this scope; substrate and pre-window incident particles require a separately defined cohort',
            'SQLite disk state and bounded cache avoid storing the whole event/particle history in Python memory']}
    json_file(directory / 'events.json', report)
    return report
