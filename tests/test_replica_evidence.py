import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from summarize_replicas import summarize


class ReplicaEvidence(unittest.TestCase):
    def fixture(self,directory):
        source=directory/'replicas.csv'
        source.write_text('case,replica,roughness\na,r1,1\na,r2,2\n')
        evidence=[]
        for index,value in enumerate((1,2),1):
            name=f'r{index}.json'
            path=directory/name;path.write_text(json.dumps({'roughness':value}))
            evidence.append({'group':{'case':'a'},'replica_id':f'r{index}','run_id':f'fixture-run-{index}',
                'seeds':{'velocity':index},'seed_basis':'Artificial explicit seed source',
                'window':{'start_ps':0,'end_ps':10,'source':'Artificial explicit window'},
                'correlation_basis':'Artificial independently reduced run scalar',
                'metric_definition':'Synthetic scalar only','unit':'angstrom',
                'metric_source':{'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'pointer':'/roughness','value_tolerance':0}})
        config={'metric_column':'roughness','unit':'angstrom','replica_id_column':'replica',
            'group_columns':['case'],'confidence':0.95,'independence_basis':'Artificial independence declaration only',
            'source_class':'research_output','observation_kind':'independent_replica_scalar','replica_evidence':evidence}
        return source,config

    def test_bound_metric_sources_keep_interval_conditional(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);source,config=self.fixture(directory)
            result=summarize(source,config,directory/'output')
            row=result['groups'][0]
            self.assertEqual(row['evidence_status'],'BOUND_DECLARATIONS')
            self.assertEqual(row['interval_status'],'CONDITIONAL_ON_DECLARED_INDEPENDENCE')
            self.assertEqual(row['mean'],1.5)
            self.assertIsNotNone(row['sem'])
            self.assertEqual(result['scientific_acceptance'],'UNVERIFIED')

    def test_missing_evidence_does_not_drop_replica_or_fabricate_sem(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);source,config=self.fixture(directory)
            config['replica_evidence'].pop()
            result=summarize(source,config,directory/'output')
            row=result['groups'][0]
            self.assertEqual(result['status'],'REPLICA_SUMMARY_PARTIAL')
            self.assertEqual(row['replicas'],2)
            self.assertEqual(row['mean'],1.5)
            self.assertIsNotNone(row['sample_sd'])
            self.assertIsNone(row['sem'])

    def test_changed_metric_source_or_repeated_run_withholds_interval(self):
        for mode in ('source','run'):
            with tempfile.TemporaryDirectory() as tmp:
                directory=Path(tmp);source,config=self.fixture(directory)
                if mode=='source':
                    (directory/'r2.json').write_text('{"roughness":99}')
                else:
                    config['replica_evidence'][1]['run_id']=config['replica_evidence'][0]['run_id']
                result=summarize(source,config,directory/'output')
                self.assertIsNone(result['groups'][0]['confidence_upper'])
                self.assertEqual(result['groups'][0]['replicas'],2)

    def test_frames_refused_and_partial_cli_is_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);source,config=self.fixture(directory)
            config['observation_kind']='trajectory_frame'
            with self.assertRaisesRegex(ValueError,'frames'):
                summarize(source,config,directory/'bad')
            config['observation_kind']='independent_replica_scalar';config['replica_evidence']=[]
            path=directory/'config.json';path.write_text(json.dumps(config))
            child=subprocess.run([sys.executable,str(ROOT/'tools/summarize_replicas.py'),'--csv',str(source),
                '--config',str(path),'--output-directory',str(directory/'partial')],capture_output=True,text=True)
            self.assertEqual(child.returncode,1,child.stderr)
            self.assertTrue((directory/'partial/replica-summary.json').is_file())


if __name__=='__main__':
    unittest.main()
