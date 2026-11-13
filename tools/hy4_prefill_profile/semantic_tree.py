"""A model hierarchy projected onto an unchanged, reviewed event ledger."""
import copy
import hashlib
import json
from pathlib import Path

from build import require, union_ns

HERE = Path(__file__).resolve().parent


def short_symbol(name):
    """Readable evidence label; the exact full symbol stays in event_evidence."""
    name = name.removeprefix('void ')
    if '<' in name:
        name = name.split('<', 1)[0] + '<…>'
    return name if len(name) <= 150 else name[:147] + '…'


def ordinal_ranges(values):
    values = sorted(values)
    ranges = []
    first = last = values[0]
    for value in values[1:]:
        if value == last + 1:
            last = value
        else:
            ranges.append(str(first) if first == last else f'{first}–{last}')
            first = last = value
    ranges.append(str(first) if first == last else f'{first}–{last}')
    return '#' + ', '.join(ranges)


def load_semantics(selection):
    name = selection.get('semantic_evidence_file')
    if name is None:
        return None
    require(name == 'representative-semantics.json', 'unsupported semantic evidence file')
    raw = (HERE / name).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == selection.get('semantic_evidence_sha256'),
            'semantic evidence checksum mismatch')
    return json.loads(raw)


def project(payload, evidence, roofs):
    """Every terminal display row owns a disjoint subset of the original events.

    An unbound family may be split into its reviewed invocations. A bound family
    cannot be split: its existing work numerator must retain its full event set.
    Parents sum known FLOPs, explicitly partial when coverage is incomplete.
    Interface bytes are never rolled up through parents.
    """
    require(evidence['source_input_sha256'] == payload['full_report_input_sha256'],
            'semantic evidence/source mismatch')
    require(evidence['event_ids_sha256'] == payload['selection']['event_ids_sha256'],
            'semantic evidence/selected event mismatch')
    originals = {c['id']: c for g in payload['groups'] for c in g['children']}
    events = {e['id']: e for e in payload['events']}
    by_owner = {ident: [e for e in events.values() if e['owner_id'] == ident]
                for ident in originals}
    claimed = []
    row_ids = set()

    def visit(spec):
        require(spec['id'] not in row_ids, 'duplicate semantic row id')
        row_ids.add(spec['id'])
        children = [visit(c) for c in spec.get('children', [])]
        if children:
            ids = [ident for c in children for ident in c['selected_event_ids']]
            ee = [events[ident] for ident in ids]
            owners = {events[ident]['owner_id'] for ident in ids}
            complete = all(originals[o]['work_bound'] and
                           originals[o]['work']['flops_by_precision'] is not None
                           and {e['id'] for e in by_owner[o]} <= set(ids)
                           for o in owners)
            parts = {}
            scalar = 0
            bound_owners = [o for o in owners if originals[o]['work_bound']]
            for o in bound_owners:
                for precision, work in (originals[o]['work']['flops_by_precision'] or {}).items():
                    parts[precision] = parts.get(precision, 0) + work
                scalar += originals[o]['work']['scalar_ops'] or 0
            active = union_ns(ee) / 1e6
            ideal = (sum(f / (roofs[p] * 1e12) for p, f in parts.items())
                     if complete and parts and set(parts) <= set(roofs) else None)
            result = dict(id=spec['id'], title=spec['title'], role=spec['role'],
                          count=len(ee), time_ms=sum(e['duration_ns'] for e in ee)/1e6,
                          union_ms=active,
                          mfu_percent=100 * ideal / (active / 1000) if ideal is not None and active else None,
                          mbu_percent=None, work_bound=complete,
                          work=dict(status='complete_reviewed_rollup' if complete else 'partial_reviewed_rollup',
                                    flops_by_precision=parts, scalar_ops=scalar,
                                    useful_bytes=None, useful_bytes_note='Interface bytes are not additive across operations.',
                                    dram_bytes=None, dram_counter_artifact_id=None),
                          children=children, selected_event_ids=ids, kind='module',
                          coverage_note=f'{len(bound_owners)}/{len(owners)} families have reviewed work joins. '
                          + ('Matrix/dot numerator complete for these captured events.' if complete else
                             'Known FLOPs are a partial sum; complete module MFU remains unavailable.'))
        else:
            owner = spec['operator_id']
            require(owner in originals, 'unknown semantic operator')
            result = copy.deepcopy(originals[owner])
            full = {e['id'] for e in by_owner[owner]}
            ids = spec.get('event_ids', [e['id'] for e in by_owner[owner]])
            require(ids and len(ids) == len(set(ids)) and set(ids) <= full,
                    'semantic row contains wrong or duplicate events')
            if set(ids) != full:
                require(not result['work_bound'], 'cannot split a reviewed work numerator')
                ee = [events[ident] for ident in ids]
                result.update(count=len(ee), time_ms=sum(e['duration_ns'] for e in ee)/1e6,
                              union_ms=union_ns(ee)/1e6, mfu_percent=None, mbu_percent=None)
            result.update(copy.deepcopy(evidence['operator_metadata'].get(owner, {})))
            result.update(id=spec['id'], operator_id=owner, selected_event_ids=ids,
                          children=[], kind='operator')
            for field in ['title', 'role', 'source', 'formula', 'shape', 'note']:
                if field in spec:
                    result[field] = spec[field]
            result['kernel_evidence'] = list(dict.fromkeys(short_symbol(evidence['event_evidence'][i]['kernel_name']) for i in ids))
            claimed.extend(ids)
        for field in ['color', 'note', 'source', 'shape']:
            if field in spec:
                result[field] = spec[field]
        ordinals = [evidence['event_evidence'][i]['selected_ordinal'] for i in result['selected_event_ids']]
        result['event_ordinals'] = ordinal_ranges(ordinals)
        result['event_ordinal_basis'] = f'Selected-layer start-order ordinal (1–{len(events)}); exact SQLite IDs are retained in evidence.'
        return result

    root = visit(evidence['tree'])
    require(len(claimed) == len(set(claimed)) and set(claimed) == set(events),
            'semantic leaves must partition selected events exactly once')
    require(root['count'] == len(events), 'semantic root count mismatch')
    require(abs(root['time_ms'] - payload['layer_metrics']['summed_residency_ms']) < 1e-9,
            'semantic root residency mismatch')
    require(abs(root['union_ms'] - payload['layer_metrics']['device_union_sum_ms']) < 1e-9,
            'semantic root union mismatch')
    return root
