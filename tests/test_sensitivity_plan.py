import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from prepare_sweep import plan_sweep


class SensitivityProposals(unittest.TestCase):
    def fixture(self,directory):
        (directory/'plan.json').write_text(json.dumps({'schema_version':1,'record_type':'md_plan','id':'fixture-plan'}))
        (directory/'base.json').write_text(json.dumps({'purpose':'research_candidate','plan_file':'plan.json','timestep_ps':None}))
        return {'purpose':'research_candidate','base_config_file':'base.json','variants':[
            {'id':'timestep-TBD','changes':{'timestep_ps':None},'reason':'Artificial numerical sensitivity proposal; preserve physical duration'}]}

    def test_unresolved_draft_proposals_do_not_prepare_inputs_or_choose_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);config=self.fixture(directory)
            original=(directory/'base.json').read_bytes()
            with patch('prepare_sweep.prepare') as preparation:
                report=plan_sweep(config,directory,directory/'proposal',1)
                preparation.assert_not_called()
            self.assertFalse(report['input_files_prepared'])
            self.assertFalse(report['execution_authorized'])
            self.assertEqual(report['jobs_submitted'],0)
            self.assertIsNone(report['proposed_variants'][0]['changes']['timestep_ps'])
            self.assertIn('parameter values',report['proposed_variants'][0]['unresolved'])
            self.assertFalse(report['base_preparation_readiness']['ready_for_local_preparation'])
            self.assertEqual((directory/'base.json').read_bytes(),original)

    def test_budget_unknown_fields_and_bad_ids_fail_before_output(self):
        for mutation in ('budget','changes','id'):
            with tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp);config=self.fixture(directory)
                maximum=1
                if mutation=='budget':maximum=0
                elif mutation=='changes':config['variants'][0]['changes']={'unknown_scientific_parameter':1}
                else:config['variants'][0]['id']={}
                with self.assertRaises(ValueError):
                    plan_sweep(config,directory,directory/'bad',maximum)
                self.assertFalse((directory/'bad').exists())


if __name__=='__main__':
    unittest.main()
