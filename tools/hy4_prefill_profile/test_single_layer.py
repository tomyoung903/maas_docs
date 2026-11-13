"""Selection safety and preservation tests, using explicitly synthetic events."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import build
import single_layer
from test_profile import fixture


def selected_fixture():
    source=fixture()
    original=source['nodes'][4]
    unknown=copy.deepcopy(original)
    unknown.update(id='r0unknown',work_matches_events=False)
    unknown['work'].update(flops_by_precision=None,useful_bytes=None,status='unavailable')
    source['nodes'].append(unknown)
    source['events'].append(dict(id='r0later',rank=0,start_ns=1_000_000,duration_ns=2_000_000,
                                owner_id=unknown['id'],artifact_id='test'))
    source['request']['execution_coverage_complete']=False
    raw=json.dumps(source).encode()
    selection=dict(source_input_sha256=hashlib.sha256(raw).hexdigest(),node_id='r0l',rank=0,
        chunk=0,layer=0,event_count=2,event_ids_sha256_format='chronological_ids_newline_terminated',
        event_ids_sha256=hashlib.sha256(b'r0e\nr0later\n').hexdigest(),
        groups=[dict(id='group',title='Synthetic test group',role='Two overlapping synthetic operators.',
                     operator_ids=['r0o','r0unknown'])])
    report=build.compile_report(source)
    report['input_sha256']=selection['source_input_sha256']
    return raw,report,selection


class SelectedLayerTests(unittest.TestCase):
    def test_preserves_complete_owned_events_and_leaf_metrics(self):
        _,report,selection=selected_fixture()
        actual=single_layer.select(report,selection)
        self.assertEqual(len(actual['events']),2)
        for event in actual['events']:
            self.assertEqual({k:v for k,v in event.items() if k!='group_id'},
                             next(e for e in report['events'] if e['id']==event['id']))
        for leaf in actual['groups'][0]['children']:
            expected=report['derived']['nodes'][leaf['id']]
            self.assertEqual(leaf['time_ms'],expected['summed_residency_ms'])
            self.assertEqual(leaf['union_ms'],expected['device_union_sum_ms'])
            self.assertEqual(leaf['mfu_percent'],expected['mfu_active_union_percent'])
            self.assertEqual(leaf['mbu_percent'],expected['estimated_mbu_active_union_percent'])
        self.assertEqual(actual['groups'][0]['time_ms'],4)
        self.assertEqual(actual['groups'][0]['union_ms'],3)
        self.assertIsNone(actual['groups'][0]['mfu_percent'])
        self.assertIsNone(actual['groups'][0]['mbu_percent'])
        self.assertIsNone(actual['layer_metrics']['mfu_active_union_percent'])

    def test_rejects_changed_source_or_event_set(self):
        for mutation in [lambda s:s.update(source_input_sha256='0'*64),
                         lambda s:s.update(event_count=1),
                         lambda s:s.update(event_ids_sha256='0'*64),
                         lambda s:s.update(event_ids_sha256_format='json'),
                         lambda s:s.update(layer=1)]:
            _,report,selection=selected_fixture();mutation(selection)
            with self.assertRaises(ValueError):single_layer.select(report,selection)

    def test_rejects_omitted_or_duplicate_operators(self):
        for ids in [['r0o'],['r0o','r0unknown','r0o'],['r0o','r1o']]:
            _,report,selection=selected_fixture();selection['groups'][0]['operator_ids']=ids
            with self.assertRaises(ValueError):single_layer.select(report,selection)

    def test_build_keeps_full_archive_but_main_embeds_only_selection(self):
        raw,_,selection=selected_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source.json';source.write_bytes(raw)
            selected=p/'selection.json';selected.write_text(json.dumps(selection))
            report=build.build(source,p/'out',selected)
            out=p/'out';html=(out/'index.html').read_text()
            embedded=html.split('<script id="selected-layer-data" type="application/json">',1)[1].split('</script>',1)[0]
            data=json.loads(embedded)
            self.assertEqual(len(data['events']),2)
            self.assertNotIn('report-data" type=',html)
            self.assertEqual((out/'source-data.json').read_bytes(),raw)
            self.assertEqual(json.loads((out/'report-data.json').read_text()),report)
            self.assertIn('data-page-key="/hy4-100k-prefill/full-report.html"',(out/'full-report.html').read_text())
            self.assertEqual(html.count('data-maas-annotator'),1)
            for anchor in ['execution-tree','method','coverage','provenance']:
                self.assertIn(f'id="{anchor}"',html)

    def test_invalid_selection_does_not_overwrite_output(self):
        raw,_,selection=selected_fixture();selection['event_count']=99
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source.json';source.write_bytes(raw)
            selected=p/'selection.json';selected.write_text(json.dumps(selection))
            out=p/'out';out.mkdir();(out/'index.html').write_text('preserve')
            with self.assertRaises(ValueError):build.build(source,out,selected)
            self.assertEqual((out/'index.html').read_text(),'preserve')
            self.assertEqual([f.name for f in out.iterdir()],['index.html'])


if __name__=='__main__':unittest.main()
