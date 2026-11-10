"""Bounded-memory descriptive time blocks; conditional intervals, never IID frame SEM."""
import math


def numeric(value, name, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or positive and value <= 0:
        raise ValueError('Explicit finite ' + name + ' required')
    return value


class Moments:
    def __init__(self):
        self.n, self.mean, self.m2 = 0, 0.0, 0.0

    def add(self, value):
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (value - self.mean)
        if not math.isfinite(self.mean) or not math.isfinite(self.m2):
            raise ValueError('Moment calculation exceeds finite numerical range')

    def result(self):
        return {'samples': self.n, 'mean': self.mean if self.n else None,
                'sample_sd': math.sqrt(max(0, self.m2) / (self.n - 1)) if self.n > 1 else None}


def analyze_samples(samples, config, emit_block=None):
    start = numeric(config.get('window_start_ps'), 'window_start_ps')
    end = numeric(config.get('window_end_ps'), 'window_end_ps')
    duration = numeric(config.get('block_duration_ps'), 'block_duration_ps', True)
    interval = numeric(config.get('sample_interval_ps'), 'sample_interval_ps', True)
    tolerance = numeric(config.get('time_tolerance_ps'), 'time_tolerance_ps')
    if end <= start or not 0 <= tolerance < interval / 2:
        raise ValueError('Increasing window and tolerance below half a sample interval required')
    span = numeric(end - start, 'finite window duration', True)
    ratio = numeric(duration / interval, 'finite block/sample ratio', True)
    expected = round(ratio)
    if expected < 1 or abs(duration - expected * interval) > tolerance:
        raise ValueError('Block duration must contain an explicit integer number of sample intervals')
    maximum = config.get('maximum_blocks')
    blocks = math.ceil(numeric(span / duration, 'finite window/block ratio', True))
    if type(maximum) is not int or maximum < 1 or blocks > maximum:
        raise ValueError('Block count exceeds explicit analysis budget')
    minimum = config.get('minimum_blocks_for_interval')
    if type(minimum) is not int or minimum < 2:
        raise ValueError('Explicit minimum_blocks_for_interval >= 2 required')
    confidence = numeric(config.get('confidence'), 'confidence')
    if not 0 < confidence < 1 or not isinstance(config.get('window_basis'), str) or not config['window_basis'].strip():
        raise ValueError('Confidence in (0,1) and explicit sampling-window basis required')
    limit = config.get('max_absolute_block_lag1')
    if limit is not None and (not 0 <= numeric(limit, 'max_absolute_block_lag1') <= 1):
        raise ValueError('Explicit lag-1 diagnostic limit must be in [0,1] or null')
    all_values, block_values, means = Moments(), Moments(), Moments()
    block_index, complete, incomplete, source_rows, excluded = 0, 0, 0, 0, 0
    previous_time, previous_grid, previous_mean = None, None, None
    pair_x, pair_y, covariance = Moments(), Moments(), 0.0
    def finish(index, values):
        nonlocal complete, incomplete, previous_mean, covariance
        lower, upper = start + index * duration, min(end, start + (index + 1) * duration)
        full = abs((upper - lower) - duration) <= tolerance and values.n == expected
        reason = None if full else 'Partial window block or missing scheduled samples'
        result = {'block': index, 'start_ps': lower, 'end_ps': upper, **values.result(),
                  'complete': full, 'reason': reason}
        if emit_block is not None:
            emit_block(result)
        if full:
            complete += 1
            means.add(values.mean)
            if previous_mean is not None:
                old_x = pair_x.mean
                pair_x.add(previous_mean)
                pair_y.add(values.mean)
                covariance += (previous_mean - old_x) * (values.mean - pair_y.mean)
            previous_mean = values.mean
        else:
            incomplete += 1
            previous_mean = None  # Never call separated blocks adjacent across a data gap.
    for time, value in samples:
        source_rows += 1
        numeric(time, 'sample time')
        numeric(value, 'sample value')
        if previous_time is not None and time <= previous_time:
            raise ValueError('Source time must be strictly increasing; no automatic reset reconciliation')
        previous_time = time
        if not start <= time < end:
            excluded += 1
            continue
        grid = round((time - start) / interval)
        if abs(time - (start + grid * interval)) > tolerance or previous_grid is not None and grid <= previous_grid:
            raise ValueError('Sample time disagrees with the explicit sampling cadence')
        previous_grid = grid
        selected_block = grid // expected
        if selected_block >= blocks:
            raise ValueError('Tolerance/grid assignment reaches outside requested window')
        while block_index < selected_block:
            finish(block_index, block_values)
            block_index += 1
            block_values = Moments()
        block_values.add(value)
        all_values.add(value)
    while block_index < blocks:
        finish(block_index, block_values)
        block_index += 1
        block_values = Moments()
    rho = covariance / math.sqrt(pair_x.m2) / math.sqrt(pair_y.m2) if pair_x.n >= 3 and pair_x.m2 > 0 and pair_y.m2 > 0 else None
    if rho is not None:
        numeric(rho, 'block lag-1 diagnostic')
        rho = max(-1.0, min(1.0, rho))
    unresolved = []
    for key in ('stationarity_basis', 'correlation_basis'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            unresolved.append('Missing declared ' + key)
    if complete < minimum:
        unresolved.append('Insufficient complete blocks')
    if incomplete:
        unresolved.append('Incomplete blocks retained; interval withheld')
    if limit is None or rho is None:
        unresolved.append('Block lag-1 sanity evidence/limit unresolved')
    elif abs(rho) > limit:
        unresolved.append('Block lag-1 diagnostic exceeds declared limit')
    block_summary = means.result()
    sem = lower = upper = None
    if not unresolved:
        from scipy.stats import t
        sem = block_summary['sample_sd'] / math.sqrt(complete)
        half = float(t.ppf((1 + confidence) / 2, complete - 1) * sem)
        lower, upper = means.mean - half, means.mean + half
        numeric(sem, 'block SEM')
        numeric(lower, 'interval lower bound')
        numeric(upper, 'interval upper bound')
    return {'status': 'CONDITIONAL_BLOCK_INTERVAL' if not unresolved else 'DESCRIPTIVE_ONLY',
            'source_rows': source_rows, 'outside_window_rows': excluded, 'selected_samples': all_values.n,
            'raw_sample_summary': all_values.result(), 'complete_blocks': complete, 'incomplete_blocks': incomplete,
            'complete_block_means': block_summary, 'adjacent_block_pairs': pair_x.n, 'block_mean_lag1_correlation': rho,
            'block_mean_sem': sem, 'confidence_lower': lower, 'confidence_upper': upper,
            'unresolved': unresolved, 'scientific_acceptance': 'UNVERIFIED',
            'assumptions': ['No IID frame SEM is computed; intervals use complete block means only',
                'Block duration, stationarity/correlation basis and diagnostic limit are supplied, not scientifically validated',
                'Lag-1 diagnostics do not establish independence or higher-lag decorrelation',
                'Conditional Student-t interval assumes approximately independent stationary block means',
                'Model error, finite size and parameter sensitivity are not represented by this statistical interval']}
