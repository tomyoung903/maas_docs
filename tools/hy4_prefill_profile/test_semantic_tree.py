"""Nonadditive timing and work-scope guards for the model hierarchy."""
import copy
import unittest

import semantic_tree
import single_layer
from test_single_layer import selected_fixture


def fixture():
    _, report, selection = selected_fixture()
    payload = single_layer.select(report, selection)
    evidence = dict(source_input_sha256=payload['full_report_input_sha256'],
                    event_ids_sha256=selection['event_ids_sha256'],
                    operator_metadata={},
                    event_evidence={e['id']: dict(selected_ordinal=i,
                                                  kernel_name='safe_kernel<float>')
                                    for i, e in enumerate(payload['events'], 1)},
                    tree=dict(id='root', title='Model root', role='Synthetic test only', children=[
                        dict(id='known', operator_id='r0o'),
                        dict(id='unknown', operator_id='r0unknown')]))
    return payload, evidence, report['hardware']['compute_roofs_tflops']


class SemanticTreeTests(unittest.TestCase):
    def test_event_ordinals_keep_disjoint_ranges_visible(self):
        self.assertEqual(semantic_tree.ordinal_ranges([1, 2, 3, 5, 7, 8]), '#1–3, 5, 7–8')

    def test_recursive_parent_uses_interval_union_and_preserves_unknown_work(self):
        payload, evidence, roofs = fixture()
        actual = semantic_tree.project(payload, evidence, roofs)
        self.assertEqual(actual['count'], 2)
        self.assertEqual(actual['time_ms'], 4)
        self.assertEqual(actual['union_ms'], 3)
        self.assertEqual(actual['work']['status'], 'partial_reviewed_rollup')
        self.assertIsNone(actual['mfu_percent'])
        self.assertIsNone(actual['mbu_percent'])
        self.assertIsNone(actual['work']['useful_bytes'])
        for child, original in zip(actual['children'], payload['groups'][0]['children']):
            for key in ['work', 'time_ms', 'union_ms', 'mfu_percent', 'mbu_percent']:
                self.assertEqual(child[key], original[key])

    def test_rejects_duplicate_omitted_and_wrong_events(self):
        for mode in ['duplicate', 'omitted', 'wrong']:
            payload, evidence, roofs = fixture()
            if mode == 'duplicate':
                evidence['tree']['children'].append(dict(id='duplicate', operator_id='r0o'))
            elif mode == 'omitted':
                evidence['tree']['children'].pop()
            else:
                evidence['tree']['children'][1]['event_ids'] = ['r0e']
            with self.assertRaises(ValueError):
                semantic_tree.project(payload, evidence, roofs)

    def test_rejects_stale_source_and_event_set(self):
        for key in ['source_input_sha256', 'event_ids_sha256']:
            payload, evidence, roofs = fixture()
            evidence[key] = '0' * 64
            with self.assertRaises(ValueError):
                semantic_tree.project(payload, evidence, roofs)

    def test_bound_scope_must_not_be_split(self):
        payload, evidence, roofs = fixture()
        extra = copy.deepcopy(payload['events'][0])
        extra.update(id='known-extra', start_ns=5_000_000)
        payload['events'].append(extra)
        evidence['event_evidence'][extra['id']] = dict(selected_ordinal=3, kernel_name='safe')
        evidence['tree']['children'][0]['event_ids'] = ['r0e']
        with self.assertRaisesRegex(ValueError, 'cannot split'):
            semantic_tree.project(payload, evidence, roofs)


if __name__ == '__main__':
    unittest.main()
