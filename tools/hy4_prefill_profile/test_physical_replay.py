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

class MoERangeTests(unittest.TestCase):
 def setUp(self):
  self.summary=json.loads((HERE/'isolated-moe-range-counters.json').read_text())
  self.selection=json.loads((HERE/'representative-selection.json').read_text())
  self.payload={'selection':self.selection,'full_report_input_sha256':self.selection['source_input_sha256'],
   'tree':{'time_ms':2.18463,'mfu_percent':17,'mbu_percent':23},'events':[{'duration_ns':2184630}]}
 def test_aggregate_uses_only_matching_range_and_preserves_trace(self):
  before=copy.deepcopy(self.payload);summary=copy.deepcopy(self.summary)
  result=physical_replay.derive_moe_range(self.summary,self.payload)
  self.assertEqual(self.payload,before);self.assertEqual(self.summary,summary)
  self.assertEqual(result['counters']['dram_total_bytes'],7515448832)
  self.assertEqual(result['counters']['l2_requested_sector_bytes'],25455027392)
  self.assertEqual(result['range_wallclock_ms'],5.20944)
  self.assertAlmostEqual(result['profiled_range_bandwidth_tb_s'],1.4426596394238152)
  for key in ('per_fc_attribution','cache_hit_ratio','physical_kernel_mbu_percent','unprofiled_latency_ms','candidate_speedup'):
   self.assertIsNone(result[key])
 def test_rejects_wrong_scope_denominator_or_unqualified_results(self):
  mutations=[lambda s:s['timing'].update(metric='gpu__time_duration.sum'),
   lambda s:s['timing'].update(deprecation_warning_at_measured_callsite=False),
   lambda s:s['collection'].update(profiling_passes=2),
   lambda s:s['numerical'].update(values_per_call=1024),
   lambda s:s['counters'].update(l2_sector_bytes=64),
   lambda s:s.update(physical_kernel_mbu_percent=18.7),
   lambda s:s['capture'].update(cached_tokens=90112)]
  for change in mutations:
   s=copy.deepcopy(self.summary);change(s)
   with self.assertRaises(ValueError):physical_replay.derive_moe_range(s,self.payload)
 def test_optional_and_checksum_bound(self):
  self.assertIsNone(physical_replay.load_moe_range({'selection':{}}))
  self.payload['selection']['moe_range_replay_sha256']='0'*64
  with self.assertRaises(ValueError):physical_replay.load_moe_range(self.payload)
class MoEFCReplayTests(unittest.TestCase):
 def setUp(self):
  self.summary=json.loads((HERE/'serialized-moe-fc-counters.json').read_text())
  self.selection=json.loads((HERE/'representative-selection.json').read_text())
  semantics=json.loads((HERE/'representative-semantics.json').read_text())
  self.payload={'selection':self.selection,'full_report_input_sha256':self.selection['source_input_sha256'],
   'event_evidence':semantics['event_evidence'],'tree':{'time_ms':2.18463,'mfu_percent':17,'mbu_percent':23},
   'events':[{'duration_ns':2184630}],'physical_replay':{'unchanged':True},'moe_range_replay':{'unchanged':True}}
 def test_exact_matched_kernel_metrics_preserve_all_other_scopes(self):
  before=copy.deepcopy(self.payload);original=copy.deepcopy(self.summary)
  result=physical_replay.derive_moe_fc(self.summary,self.payload,7.7)
  self.assertEqual(self.payload,before);self.assertEqual(self.summary,original)
  a,b=result['rows'];self.assertEqual((a['total_bytes'],b['total_bytes']),(3923638016,2685093632))
  self.assertEqual((a['profiled_duration_ms'],b['profiled_duration_ms']),(1.166176,0.62448))
  self.assertAlmostEqual(a['matched_physical_mbu_percent'],43.695237999)
  self.assertAlmostEqual(b['matched_physical_mbu_percent'],55.840612782)
  for key in ('original_concurrent_physical_mbu_percent','native_expected_latency_ms','unprofiled_latency_ms','candidate_speedup'):self.assertIsNone(result[key])
 def test_duration_scope_and_qualification_mutations_rejected(self):
  changes=[lambda s:s['rows'][0].update(duration_metric='gpu__time_duration_measured_wallclock.sum'),
   lambda s:s['collection'].update(replay_mode='app-range'),lambda s:s['collection'].update(original_native_overlap_preserved=True),
   lambda s:s['capture'].update(cached_tokens=90112),lambda s:s['rows'][0].update(profiling_passes=2),
   lambda s:s['numerical'].update(values_per_call=1),lambda s:s.update(native_expected_latency_ms=1),
   lambda s:s['rows'][0]['launch_geometry_and_resources'].update(launch__grid_dim_y=493),
   lambda s:s['rows'][1].update(cluster_dimensions=[0,0,0]),
   lambda s:s.update(artifacts=[a for a in s['artifacts'] if a['label']!='independent actual counter audit'])]
  for change in changes:
   item=copy.deepcopy(self.summary);change(item)
   with self.assertRaises(ValueError):physical_replay.derive_moe_fc(item,self.payload,7.7)
 def test_roof_private_data_and_checksum(self):
  with self.assertRaises(ValueError):physical_replay.derive_moe_fc(self.summary,self.payload,8)
  self.summary['artifacts'].append({'label':'/workspace/private','sha256':'0'*64})
  with self.assertRaises(ValueError):physical_replay.derive_moe_fc(self.summary,self.payload,7.7)
  self.payload['selection']['moe_fc_replay_sha256']='0'*64
  with self.assertRaises(ValueError):physical_replay.load_moe_fc(self.payload,7.7)
  self.assertIsNone(physical_replay.load_moe_fc({'selection':{}},7.7))

if __name__=='__main__':unittest.main()
