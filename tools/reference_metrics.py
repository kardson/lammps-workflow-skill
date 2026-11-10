"""Compare explicitly aligned reference/prediction records without inference or fitting."""
import math


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def matrix(value, count):
    return isinstance(value, list) and len(value) == count and all(
        isinstance(row, list) and len(row) == 3 and all(finite(x) for x in row) for row in value)


def summary(errors):
    scale = max(map(abs, errors)) if errors else None
    return {'count': len(errors), 'mae': math.fsum(abs(value) / len(errors) for value in errors) if errors else None,
            'rmse': scale * math.sqrt(math.fsum((value / scale) ** 2 for value in errors) / len(errors)) if scale else scale,
            'max_absolute': scale}


def evaluate(references, predictions, requested=('energy', 'forces')):
    if not requested or len(set(requested)) != len(requested) or any(metric not in ('energy', 'forces', 'stress') for metric in requested):
        raise ValueError('Explicit supported metric selection required')
    def indexed(records, kind):
        mapping = {}
        for record in records:
            key = record.get('id')
            if not isinstance(key, str) or not key or key in mapping:
                raise ValueError('Missing/duplicate ' + kind + ' sample ID')
            mapping[key] = record
        return mapping
    refs, preds = indexed(references, 'reference'), indexed(predictions, 'prediction')
    reports, force_errors, energy_groups, stress_groups = [], {}, {}, {}
    coverage = {metric: {'required': len(refs), 'valid': 0, 'missing_label': 0, 'unavailable': 0}
                for metric in requested}
    for metric in requested:
        if metric == 'energy':
            labeled = sum(finite(record.get('energy_eV')) for record in refs.values())
        elif metric == 'forces':
            labeled = sum(isinstance(record.get('species'), list) and bool(record['species']) and matrix(record.get('forces_eV_per_angstrom'), len(record['species'])) for record in refs.values())
        else:
            labeled = sum(matrix(record.get('stress'), 3) for record in refs.values())
        coverage[metric].update(reference_labels_available=labeled, reference_labels_missing_or_invalid=len(refs) - labeled)
    for key, reference in refs.items():
        prediction = preds.get(key)
        representation = reference.get('species_representation', 'unknown')
        if representation not in ('ordinary_atoms', 'pseudo_atoms', 'unknown'):
            raise ValueError('Unsupported reference species_representation')
        item = {'id': key, 'metrics': {}, 'issues': [], 'dft_group': reference.get('dft_group'),
                'species_representation': representation,
                'reference_domain_status': 'PSEUDO_ATOM_ADAPTER_UNSUPPORTED' if representation == 'pseudo_atoms' else 'UNQUALIFIED_DIAGNOSTIC' if representation == 'unknown' else 'ORDINARY_ATOMS_DECLARED_NOT_ACCEPTED',
                'energy_reference': reference.get('energy_reference'),
                'configuration_sha256': reference.get('configuration_sha256'),
                'reference_provenance': reference.get('provenance', []),
                'prediction_provenance': prediction.get('provenance', []) if prediction else []}
        reports.append(item)
        if representation == 'pseudo_atoms':
            item['prediction_status'] = 'MISSING' if prediction is None else prediction.get('status', 'UNKNOWN')
            item['issues'].append('Pseudo-atom reference cannot be silently compared as ordinary element species; a separately justified physical mapping/adapter is required')
            for metric in requested:
                coverage[metric]['unavailable'] += 1
            continue
        if prediction is None or prediction.get('status') != 'SUCCEEDED':
            item['prediction_status'] = 'MISSING' if prediction is None else prediction.get('status', 'UNKNOWN')
            item['issues'].append('Prediction missing or not successful: ' + str((prediction or {}).get('reason', '')))
            for metric in requested:
                coverage[metric]['unavailable'] += 1
            continue
        item['prediction_status'] = 'SUCCEEDED'
        if reference.get('configuration_sha256') is not None or prediction.get('configuration_sha256') is not None:
            if not reference.get('configuration_sha256') or reference.get('configuration_sha256') != prediction.get('configuration_sha256'):
                item['issues'].append('Configuration identity mismatch or absent')
                for metric in requested:
                    coverage[metric]['unavailable'] += 1
                continue
        species = reference.get('species')
        if not isinstance(species, list) or not species or not all(isinstance(s, str) and s for s in species) or species != prediction.get('species'):
            item['issues'].append('Species/order mismatch or absent; no guessed atom remapping')
            for metric in requested:
                coverage[metric]['unavailable'] += 1
            continue
        for metric in requested:
            if metric == 'energy':
                actual, predicted = reference.get('energy_eV'), prediction.get('energy_eV')
                if not finite(actual):
                    coverage[metric]['missing_label'] += 1
                    item['issues'].append('Reference energy missing/nonfinite')
                    continue
                convention = reference.get('energy_reference')
                group = reference.get('dft_group')
                if not finite(predicted) or not isinstance(convention, str) or not convention or convention != prediction.get('energy_reference') or not isinstance(group, str) or not group:
                    coverage[metric]['unavailable'] += 1
                    item['issues'].append('Energy prediction/reference alignment or DFT group unresolved')
                    continue
                error = (predicted - actual) / len(species)
                if not finite(error):
                    coverage[metric]['unavailable'] += 1
                    item['issues'].append('Energy error overflow')
                    continue
                item['metrics'][metric] = {'signed_error_eV_per_atom': error}
                partition = (group, convention, tuple(sorted(species)))
                energy_groups.setdefault(partition, []).append(error)
            elif metric == 'forces':
                actual, predicted = reference.get('forces_eV_per_angstrom'), prediction.get('forces_eV_per_angstrom')
                if not matrix(actual, len(species)):
                    coverage[metric]['missing_label'] += 1
                    item['issues'].append('Reference forces missing/nonfinite/wrong shape')
                    continue
                if not matrix(predicted, len(species)):
                    coverage[metric]['unavailable'] += 1
                    item['issues'].append('Predicted forces missing/nonfinite/wrong shape')
                    continue
                errors = []
                for symbol, ref_row, pred_row in zip(species, actual, predicted):
                    atom_errors = [p - r for p, r in zip(pred_row, ref_row)]
                    errors += atom_errors
                if not all(finite(error) for error in errors):
                    coverage[metric]['unavailable'] += 1
                    item['issues'].append('Force error overflow')
                    continue
                for index, symbol in enumerate(species):
                    atom_errors = errors[index * 3:index * 3 + 3]
                    force_errors.setdefault(symbol, []).extend(atom_errors)
                item['metrics'][metric] = summary(errors)
            else:
                actual, predicted = reference.get('stress'), prediction.get('stress')
                if not matrix(actual, 3):
                    coverage[metric]['missing_label'] += 1
                    item['issues'].append('Reference stress missing/nonfinite/wrong shape')
                    continue
                unit, convention = reference.get('stress_unit'), reference.get('stress_convention')
                if not matrix(predicted, 3) or not isinstance(unit, str) or not unit or not isinstance(convention, str) or not convention or unit != prediction.get('stress_unit') or convention != prediction.get('stress_convention'):
                    coverage[metric]['unavailable'] += 1
                    item['issues'].append('Stress prediction/unit/sign/order convention unresolved')
                    continue
                errors = [p - r for ref_row, pred_row in zip(actual, predicted) for p, r in zip(pred_row, ref_row)]
                if not all(finite(error) for error in errors):
                    coverage[metric]['unavailable'] += 1
                    item['issues'].append('Stress error overflow')
                    continue
                stress_groups.setdefault((unit, convention), []).extend(errors)
                item['metrics'][metric] = summary(errors)
            coverage[metric]['valid'] += 1
    extra = sorted(set(preds) - set(refs))
    complete = bool(refs) and not extra and all(value['valid'] == value['required'] for value in coverage.values())
    ranked = {}
    for metric, field in (('energy', 'signed_error_eV_per_atom'), ('forces', 'max_absolute')):
        values = [{'id': sample['id'], 'absolute_error': abs(sample['metrics'][metric][field]),
                   'dft_group': sample['dft_group'], 'energy_reference': sample['energy_reference']}
                  for sample in reports if metric in sample['metrics']]
        ranked[metric] = {'valid_samples': len(values), 'largest_first_100': sorted(values,
            key=lambda item: (-item['absolute_error'], item['id']))[:100],
            'scope': 'Largest observed errors, not a threshold-based rejection or exclusion'}
    return {'status': 'METRICS_REPORTED_NOT_ACCEPTED' if complete else 'METRICS_PARTIAL',
            'total_reference_samples': len(refs), 'prediction_records': len(preds), 'extra_prediction_ids': extra,
            'prediction_accounting': {'records_supplied_for_reference': sum(key in preds for key in refs),
                'declared_succeeded': sum(preds[key].get('status') == 'SUCCEEDED' for key in refs if key in preds),
                'declared_failed': sum(preds[key].get('status') == 'FAILED' for key in refs if key in preds),
                'missing_records': sum(key not in preds for key in refs),
                'other_status': sum(preds[key].get('status') not in ('SUCCEEDED', 'FAILED') for key in refs if key in preds)},
            'coverage': coverage, 'samples': reports, 'ranked_errors': ranked,
            'reference_domain_coverage': {name: sum(sample['species_representation'] == name for sample in reports)
                                          for name in ('ordinary_atoms', 'pseudo_atoms', 'unknown')},
            'force_components_by_species_eV_per_angstrom': {key: summary(values) for key, values in force_errors.items()},
            'energy_groups': [{'dft_group': key[0], 'energy_reference': key[1], 'composition': list(key[2]),
                               'errors_eV_per_atom': summary(values)} for key, values in energy_groups.items()],
            'stress_groups': [{'unit': key[0], 'convention': key[1], 'errors': summary(values)} for key, values in stress_groups.items()],
            'scientific_acceptance': 'UNVERIFIED', 'inference_performed': False,
            'limitations': ['Explicitly supplied alignment only; no energy offsets fitted or inferred',
                           'Energy groups retain composition, convention and supplied DFT group',
                           'Stress compared only with identical declared unit/sign/order convention',
                           'Reference convergence/physical adequacy and prediction provenance require separate review',
                           'Component metrics are not independent-sample uncertainty estimates']}
