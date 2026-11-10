"""Explicit frame-index phase mapping, including declared restart step origins."""
import math


class TimeMapper:
    def __init__(self, segments):
        self.segments = segments
        self.previous_time = None
        self.mapped = 0
        self.unmapped = 0
        if segments is None:
            return
        if not isinstance(segments, list) or not segments:
            raise ValueError('time_segments must be a nonempty explicit list or omitted')
        end, ids = 0, set()
        for item in segments:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or item['id'] in ids:
                raise ValueError('Explicit unique time-segment IDs required')
            ids.add(item['id'])
            first, last = item.get('first_frame'), item.get('last_frame_exclusive')
            if type(first) is not int or type(last) is not int or first < end or last <= first:
                raise ValueError('Ordered nonoverlapping half-open frame ranges required')
            end = last
            if type(item.get('step_origin')) is not int or item['step_origin'] < 0:
                raise ValueError('Explicit nonnegative step origin required')
            for key in ('time_origin_ps', 'timestep_ps'):
                value = item.get(key)
                if type(value) not in (int, float) or not math.isfinite(value) or key == 'timestep_ps' and value <= 0:
                    raise ValueError('Explicit finite time origin and positive timestep required')
            if not isinstance(item.get('source'), str) or not item['source'].strip():
                raise ValueError('Time-segment source required; no inferred timestep or restart offset')

    def map(self, index, step):
        if self.segments is None:
            return {'phase_id': None, 'time_ps': None, 'timeline_status': 'NOT_SUPPLIED'}
        matches = [item for item in self.segments if item['first_frame'] <= index < item['last_frame_exclusive']]
        if not matches:
            self.unmapped += 1
            return {'phase_id': None, 'time_ps': None, 'timeline_status': 'UNMAPPED_FRAME'}
        segment = matches[0]
        if type(step) is not int or step < segment['step_origin']:
            raise ValueError('Frame step precedes declared phase origin')
        time = segment['time_origin_ps'] + (step - segment['step_origin']) * segment['timestep_ps']
        if not math.isfinite(time) or self.previous_time is not None and time <= self.previous_time:
            raise ValueError('Mapped physical timeline is nonfinite/repeated/decreasing; reconcile phases explicitly')
        self.previous_time = time
        self.mapped += 1
        return {'phase_id': segment['id'], 'time_ps': time, 'timeline_status': 'EXPLICITLY_MAPPED'}
