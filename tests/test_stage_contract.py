import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from stage_contract import audit, inspect_observation


class StageContracts(unittest.TestCase):
    def test_schema_and_malformed_records(self):
        import jsonschema
        schema = json.loads((ROOT / 'schemas/stage-contract.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        template = json.loads((ROOT / 'templates/stage-contract.json').read_text())
        self.assertEqual(audit(template)['status'], 'PARTIAL')
        for data in ([], {'schema_version': 99}, {**self.contract(), 'stages': [{'id': []}]}):
            self.assertEqual(audit(data)['status'], 'INVALID')
        contract = self.contract()
        contract['stages'][0]['integrators'][0]['fix_id'] = []
        self.assertEqual(audit(contract)['status'], 'INVALID')

    def test_cli_partial_and_bad_observation_usage(self):
        command = [sys.executable, str(ROOT / 'tools/inspect_stages.py'), '--contract', str(ROOT / 'templates/stage-contract.json')]
        child = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(child.returncode, 1, child.stderr)
        self.assertEqual(json.loads(child.stdout)['status'], 'PARTIAL')
        child = subprocess.run(command + ['--stage', 'deposition'], capture_output=True, text=True)
        self.assertEqual(child.returncode, 2)
        self.assertEqual(json.loads(child.stdout)['status'], 'ERROR')

    def contract(self):
        return {'schema_version': 1, 'record_type': 'deposition_stage_contract', 'plan_binding': {'id': 'fixture'},
            'stages': [{'id': 'fixture-growth', 'kind': 'deposition', 'start_step': 0, 'end_step': 10,
            'timestep_ps': 0.001, 'physical_time_origin_ps': 0,
            'group_roles': {'fixed': 'base', 'bath': 'bath', 'mobile': 'mobile', 'incoming': 'incoming'},
            'integrators': [{'fix_id': 'move', 'atom_ids': [2, 3]}], 'particle_count_varies': True, 'open_system': True,
            'temperature_definition': {'compute_id': 't', 'selection': 'mobile', 'streaming_velocity_treatment': 'Explicit fixture rule',
            'dynamic_dof': True, 'extra_dof': 0, 'definition': 'Artificial temperature contract'},
            'heat_flow_definition': 'Artificial fixture only', 'insertion_event_definition': 'Actual successful counter required',
            'engine_support': {'source': 'Artificial fixture, not a runtime claim'},
            'stop_conditions': [{'id': 'high-temperature', 'quantity': 'temperature', 'operator': 'gt', 'threshold': 1000,
             'unit': 'K', 'reason': 'Artificial high-temperature fixture', 'source': 'Synthetic test threshold, not research default'}]}]}

    def test_missing_choices_remain_partial(self):
        contract = self.contract()
        contract['stages'][0]['temperature_definition'] = None
        self.assertEqual(audit(contract)['status'], 'PARTIAL')

    def test_duplicate_integration_and_open_energy_criterion_rejected(self):
        contract = self.contract()
        stage = contract['stages'][0]
        stage['integrators'].append({'fix_id': 'also-move', 'atom_ids': [3]})
        self.assertEqual(audit(contract)['status'], 'INVALID')
        stage['integrators'].pop()
        stage['stop_conditions'][0]['quantity'] = 'closed_system_total_energy_drift'
        self.assertEqual(audit(contract)['status'], 'INVALID')

    def test_trigger_is_report_only_and_missing_unit_is_unknown(self):
        contract = self.contract()
        original = copy.deepcopy(contract)
        observation = {'step': 5, 'source': 'Artificial supplied observation',
                       'quantities': {'temperature': {'value': 1200, 'unit': 'K'}}}
        result = inspect_observation(contract, 'fixture-growth', observation)
        self.assertEqual(result['status'], 'CONDITION_TRIGGERED')
        self.assertFalse(result['process_action_performed'])
        self.assertEqual(contract, original)
        observation['quantities']['temperature']['unit'] = 'unknown'
        self.assertEqual(inspect_observation(contract, 'fixture-growth', observation)['status'], 'UNVERIFIED')
        observation['step'] = 10
        self.assertEqual(inspect_observation(contract, 'fixture-growth', observation)['status'], 'UNVERIFIED')

    def test_incomplete_stop_condition_cannot_trigger(self):
        contract = self.contract()
        contract['stages'][0]['stop_conditions'][0]['operator'] = None
        observation = {'step': 5, 'source': 'Artificial supplied observation',
                       'quantities': {'temperature': {'value': 1200, 'unit': 'K'}}}
        self.assertEqual(inspect_observation(contract, 'fixture-growth', observation)['status'], 'UNVERIFIED')

    def test_malformed_measurement_and_nonfinite_value_stay_unknown(self):
        contract = self.contract()
        observation = {'step': 5, 'source': 'Artificial supplied observation', 'quantities': {'temperature': None}}
        self.assertEqual(inspect_observation(contract, 'fixture-growth', observation)['status'], 'UNVERIFIED')
        observation['quantities']['temperature'] = {'value': float('nan'), 'unit': 'K'}
        result = inspect_observation(contract, 'fixture-growth', observation)
        self.assertIsNone(result['checks'][0]['value'])
        json.dumps(result, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
