"""Metric completion must never silently turn unknown bytes into matrix coverage."""
import copy
import json
from pathlib import Path
import unittest

import metric_completion
import semantic_tree
from test_semantic_tree import fixture


def setup():
    payload, evidence, roofs = fixture()
    payload['tree'] = semantic_tree.project(payload, evidence, roofs)
    completion = dict(source_input_sha256=payload['full_report_input_sha256'],
        selected_event_ids_sha256=payload['selection']['event_ids_sha256'],
        matrix_scope_definition='Synthetic reviewed projection scope.',
        source_pins=[], limits=[], scalar_convention='Synthetic only.',
        entries=[dict(operator_id='r0unknown', event_ids=['r0later'],
            matrix_scope_reviewed=True, matrix_flops_by_precision={},
            source_anchors=[dict(label='synthetic.py', line=1, anchor='copy')],
            matrix_scope_note='Synthetic memory copy; no matrix work.',
            scalar_ops=None, useful_bytes=None, dram_bytes=None, dram_counter_artifact_id=None,
            family='synthetic_copy', operation_kind='memory_copy')])
    return payload, completion, roofs


class MetricCompletionTests(unittest.TestCase):
    def test_completes_matrix_scope_without_mutating_original_work_or_byte_coverage(self):
        payload, completion, roofs = setup()
        preserved = copy.deepcopy({k: payload[k] for k in ['groups', 'events', 'layer_metrics']})
        old_work = copy.deepcopy([c['work'] for c in payload['tree']['children']])
        metric_completion.apply(payload, completion, roofs, 1)
        root = payload['tree']
        self.assertTrue(root['compute_work']['complete'])
        ideal = sum(v / roofs[p] / 1e12 for p,v in root['compute_work']['flops_by_precision'].items())
        self.assertEqual(root['mfu_percent'], 100*ideal/(root['union_ms']/1000))
        self.assertEqual(root['union_ms'], 3)
        self.assertEqual(root['time_ms'], 4)
        self.assertIsNone(root['mbu_percent'])
        self.assertFalse(root['scalar_work']['coverage_complete'])
        self.assertFalse(root['children'][1]['work_bound'])
        self.assertIsNone(root['children'][1]['additional_work']['useful_bytes'])
        self.assertEqual([c['work'] for c in root['children']], old_work)
        self.assertEqual({k: payload[k] for k in preserved}, preserved)

    def test_useful_bytes_are_leaf_only_and_do_not_become_physical_dram(self):
        payload, completion, roofs = setup()
        completion['entries'][0]['useful_bytes'] = 2_000_000
        metric_completion.apply(payload, completion, roofs, 1)
        self.assertEqual(payload['tree']['children'][1]['mbu_percent'], .1)
        self.assertIsNone(payload['tree']['mbu_percent'])
        self.assertIsNone(payload['tree']['work']['useful_bytes'])
        self.assertIsNone(payload['matrix_scope_metrics']['measured_physical_dram_mbu'])

    def test_rejects_stale_evidence_wrong_events_and_invented_flops_or_counters(self):
        for mutation in [lambda d:d.update(source_input_sha256='wrong'),
                         lambda d:d.update(selected_event_ids_sha256='wrong'),
                         lambda d:d['entries'][0].update(event_ids=['r0e']),
                         lambda d:d['entries'][0].update(matrix_flops_by_precision={'bf16':100}),
                         lambda d:d['entries'][0].update(dram_bytes=100),
                         lambda d:d['entries'].append(copy.deepcopy(d['entries'][0]))]:
            payload, completion, roofs = setup()
            mutation(completion)
            with self.assertRaises(ValueError):metric_completion.apply(payload, completion, roofs, 1)

    def test_cannot_replace_an_original_bound_numerator(self):
        payload, completion, roofs = setup()
        completion['entries'][0].update(operator_id='r0o', event_ids=['r0e'])
        with self.assertRaisesRegex(ValueError, 'existing reviewed'):
            metric_completion.apply(payload, completion, roofs, 1)

    def test_missing_classification_keeps_parent_unknown(self):
        payload, completion, roofs = setup()
        completion['entries'] = []
        metric_completion.apply(payload, completion, roofs, 1)
        self.assertFalse(payload['tree']['compute_work']['complete'])
        self.assertIsNone(payload['tree']['mfu_percent'])

    def test_split_scalar_scope_requires_exact_event_allocation(self):
        payload, completion, roofs = setup()
        second = copy.deepcopy(payload['events'][1])
        second.update(id='extra', start_ns=5_000_000)
        payload['events'].append(second)
        original = payload['tree']['children'][1]
        extra_row = copy.deepcopy(original)
        extra_row.update(id='extra-row', selected_event_ids=['extra'])
        payload['tree']['children'].append(extra_row)
        completion['entries'][0].update(event_ids=['r0later','extra'], scalar_ops=3)
        with self.assertRaisesRegex(ValueError, 'per-event allocation'):
            metric_completion.apply(payload, completion, roofs, 1)
        completion['entries'][0]['per_event_scalar_ops'] = {'r0later':1,'extra':2}
        metric_completion.apply(payload, completion, roofs, 1)
        self.assertEqual(payload['tree']['children'][1]['additional_work']['scalar_ops'],1)
        self.assertEqual(payload['tree']['children'][2]['additional_work']['scalar_ops'],2)

    def test_frozen_hy4_completion_preserves_six_exact_byte_scopes_and_rope_sum(self):
        completion=json.loads((Path(__file__).parent/'representative-metric-completion.json').read_text())
        entries={e['family']:e for e in completion['entries']}
        self.assertEqual(len(entries),13)
        self.assertEqual(sum(len(e['event_ids']) for e in entries.values()),17)
        self.assertEqual({k:v['useful_bytes'] for k,v in entries.items() if v['useful_bytes'] is not None},
            dict(rmsnorm=83_891_200,indexer_k_layernorm=4_195_328,indexer_hadamard=138_412_032,
                 indexer_activation_fp8_quant=101_711_872,kv_fp8_quant=14_811_136,
                 aten_metadata_elementwise=67_108_864))
        self.assertEqual(entries['rope']['scalar_ops'],sum(entries['rope']['per_event_scalar_ops'].values()))
        self.assertTrue(all(e['matrix_flops_by_precision']=={} for e in entries.values()))
        self.assertTrue(all(e['dram_bytes'] is None for e in entries.values()))


if __name__ == '__main__': unittest.main()
