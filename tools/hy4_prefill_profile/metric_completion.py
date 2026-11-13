"""Extend selected-tree metrics without rewriting the original work ledger."""
import copy
import hashlib
import json
from pathlib import Path

from build import require

HERE = Path(__file__).resolve().parent


def load_completion(selection):
    name = selection.get('metric_completion_file')
    if name is None:
        return None
    require(name == 'representative-metric-completion.json', 'unsupported metric completion file')
    raw = (HERE / name).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == selection.get('metric_completion_sha256'),
            'metric completion checksum mismatch')
    return json.loads(raw)


def apply(payload, completion, roofs, bandwidth):
    """Add matrix coverage and per-field evidence, preserving original work objects.

    Newly classified scopes are non-matrix operations. Their empty matrix FLOP
    numerator says nothing about scalar arithmetic, useful bytes or DRAM traffic.
    Splitting a family's scalar work requires exact per-event allocation.
    """
    require(completion['source_input_sha256'] == payload['full_report_input_sha256'],
            'completion/source mismatch')
    require(completion['selected_event_ids_sha256'] == payload['selection']['event_ids_sha256'],
            'completion/selected-event mismatch')
    originals = {c['id']: c for g in payload['groups'] for c in g['children']}
    by_owner = {owner: {e['id'] for e in payload['events'] if e['owner_id'] == owner}
                for owner in originals}
    entries = {}
    for entry in completion['entries']:
        owner = entry['operator_id']
        require(owner in originals and owner not in entries, 'unknown or duplicate completion owner')
        require(not originals[owner]['work_bound'], 'completion cannot replace an existing reviewed work binding')
        require(set(entry['event_ids']) == by_owner[owner]
                and len(entry['event_ids']) == len(set(entry['event_ids'])),
                'completion must cover the exact original event set')
        require(entry['matrix_scope_reviewed'] is True and entry['matrix_flops_by_precision'] == {},
                'completion accepts only explicitly reviewed non-matrix work')
        require(entry.get('source_anchors') and entry.get('matrix_scope_note'), 'completion evidence missing')
        require(entry.get('dram_bytes') is None and entry.get('dram_counter_artifact_id') is None,
                'source completion cannot invent DRAM counters')
        require(entry.get('useful_bytes') is None or entry['useful_bytes'] >= 0,
                'negative useful-byte estimate')
        entries[owner] = entry

    seen = set()

    def visit(row):
        if row['children']:
            for child in row['children']:
                visit(child)
            complete = all(c['compute_work']['complete'] for c in row['children'])
            parts = {}
            for child in row['children']:
                for precision, value in child['compute_work']['flops_by_precision'].items():
                    parts[precision] = parts.get(precision, 0) + value
            row['compute_work'] = dict(complete=complete, flops_by_precision=parts,
                                       definition=completion['matrix_scope_definition'])
            row['scalar_work'] = dict(known_ops=sum(c['scalar_work']['known_ops'] for c in row['children']),
                                     coverage_complete=all(c['scalar_work']['coverage_complete'] for c in row['children']))
            ideal = (sum(value / roofs[p] / 1e12 for p, value in parts.items())
                     if complete and parts and set(parts) <= set(roofs) else None)
            row['mfu_percent'] = 100 * ideal / (row['union_ms'] / 1000) if ideal is not None and row['union_ms'] else None
            row['coverage_note'] = ('Matrix-work scope is reviewed for every captured child. Scalar work and byte coverage are separate.'
                                    if complete else 'Matrix-work scope remains incomplete for these captured children.')
            # Parent interfaces are deliberately never summed.
            row['mbu_percent'] = None
            return

        owner = row['operator_id']
        original = originals[owner]
        parts = copy.deepcopy(original['work']['flops_by_precision'] or {})
        complete = original['work_bound'] and original['work']['flops_by_precision'] is not None
        if owner in entries:
            entry = copy.deepcopy(entries[owner])
            ids = set(row['selected_event_ids'])
            require(ids <= by_owner[owner], 'completion leaf has wrong events')
            if ids != by_owner[owner]:
                require(entry['useful_bytes'] is None, 'split completion bytes need a separate reviewed allocation')
                if entry['scalar_ops'] is not None:
                    per_event = entry.get('per_event_scalar_ops', {})
                    require(set(per_event) == by_owner[owner] and sum(per_event.values()) == entry['scalar_ops'],
                            'split scalar scope needs an exact per-event allocation')
                    entry['scalar_ops'] = sum(per_event[i] for i in ids)
                    entry['scalar_formula'] = ' + '.join(entry.get('per_event_scalar_formula', {}).get(i, str(per_event[i])) for i in sorted(ids))
            entry['event_ids'] = row['selected_event_ids']
            if len(ids) == 1 and entry.get('per_event_shape'):
                entry['shape'] = entry['per_event_shape'][next(iter(ids))]
            row['additional_work'] = entry
            if entry.get('shape'):
                row['shape'] = entry['shape']
            if entry.get('title'):
                row['title'] = entry['title']
            if entry['family'] == 'indexer_cache_store':
                row['role'] = 'Quantize BF16 keys to FP8, generate their scales, and scatter them into the indexer cache.'
            row['actual_mode'] = entry['operation_kind'].replace('_', ' ')
            row['mbu_percent'] = (100 * entry['useful_bytes'] / (bandwidth * 1e12 * row['union_ms'] / 1000)
                                   if entry['useful_bytes'] is not None and bandwidth and row['union_ms'] else None)
            complete = True
            parts = {}
            seen.add(owner)
        scalar = row.get('additional_work', original['work']).get('scalar_ops')
        row['scalar_work'] = dict(known_ops=scalar or 0, coverage_complete=scalar is not None)
        row['compute_work'] = dict(complete=bool(complete), flops_by_precision=parts,
                                  definition=completion['matrix_scope_definition'])

    visit(payload['tree'])
    require(seen == set(entries), 'completion owner missing from semantic tree')
    root = payload['tree']
    payload['matrix_scope_metrics'] = dict(coverage_complete=root['compute_work']['complete'],
        classified_families=sum(o['work_bound'] and o['work']['flops_by_precision'] is not None for o in originals.values()) + len(entries),
        total_families=len(originals), selected_events=len(payload['events']),
        flops_by_precision=root['compute_work']['flops_by_precision'],
        nominal_mfu_active_union_percent=root['mfu_percent'], active_union_ms=root['union_ms'],
        measured_physical_dram_mbu=None,
        definition=completion['matrix_scope_definition'])
    payload['metric_completion_evidence'] = dict(source_pins=completion['source_pins'], limits=completion['limits'],
        scalar_convention=completion['scalar_convention'],
        evidence_file=payload['selection'].get('metric_completion_file'),
        evidence_sha256=payload['selection'].get('metric_completion_sha256'))
