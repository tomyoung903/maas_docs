"""Counter denominators and separation from original trace metrics."""
import copy
import json
from pathlib import Path
import unittest
import physical_replay

HERE=Path(__file__).resolve().parent

class PhysicalReplayTests(unittest.TestCase):
 def setUp(self):
  self.summary=json.loads((HERE/'isolated-replay-counters.json').read_text())
  self.selection=json.loads((HERE/'representative-selection.json').read_text())
  self.payload={'selection':self.selection,'full_report_input_sha256':self.selection['source_input_sha256'],
   'event_evidence':{r['original_event_id']:{'kernel_name':r['kernel_name'],'kernel_symbol_sha256':r['kernel_symbol_sha256']} for r in self.summary['rows']},
   'tree':{'time_ms':999,'mfu_percent':17,'mbu_percent':23},'events':[{'duration_ns':123456789}]}
 def test_uses_counter_duration_and_preserves_original(self):
  before=copy.deepcopy(self.payload);s=copy.deepcopy(self.summary)
  result=physical_replay.derive(self.summary,self.payload,7.7)
  self.assertEqual(self.payload,before);self.assertEqual(self.summary,s)
  a,b=result['rows'];self.assertEqual(a['total_bytes'],3285081088);self.assertEqual(b['total_bytes'],5460632064)
  self.assertAlmostEqual(a['matched_physical_mbu_percent'],16.608295995502473)
  self.assertAlmostEqual(b['matched_physical_mbu_percent'],73.58031841660116)
  self.assertEqual(a['profiled_duration_ms'],2.5688)
 def test_changed_roof_rejected(self):
  with self.assertRaises(ValueError):physical_replay.derive(self.summary,self.payload,8.0)
 def test_changed_symbol_rejected(self):
  self.summary['rows'][0]['kernel_name']+=' changed'
  with self.assertRaises(ValueError):physical_replay.derive(self.summary,self.payload,7.7)
 def test_changed_selection_rejected(self):
  self.payload['selection']['new_tokens']=4096
  with self.assertRaises(ValueError):physical_replay.derive(self.summary,self.payload,7.7)
 def test_multi_pass_rejected(self):
  self.summary['rows'][0]['profiling_passes']=2
  with self.assertRaises(ValueError):physical_replay.derive(self.summary,self.payload,7.7)
 def test_interrupted_chain_rejected(self):
  self.summary['collection']['intermediate_host_copy']=True
  with self.assertRaises(ValueError):physical_replay.derive(self.summary,self.payload,7.7)
 def test_private_path_rejected(self):
  self.summary['artifacts'].append({'label':'/workspace/private-input','sha256':'0'*64})
  with self.assertRaises(ValueError):physical_replay.derive(self.summary,self.payload,7.7)
 def test_optional_replay_not_attached_to_unrelated_fixture(self):
  self.assertIsNone(physical_replay.load_replay({'selection':{}},7.7))
if __name__=='__main__':unittest.main()
