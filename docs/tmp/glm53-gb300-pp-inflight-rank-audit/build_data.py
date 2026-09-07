"""Build sanitized chart data from the read-only PP inflight audit capture."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    output = Path(__file__).parent
    raw_path = args.capture / 'inflight.json'
    raw = json.loads(raw_path.read_text())['data']['result']
    audit = json.loads((args.capture / 'analysis.json').read_text())
    metadata = json.loads((args.capture / 'metadata.json').read_text())
    time = sorted({int(t) for row in raw for t, _ in row['values']})
    assert len(time) == 961 and all(b - a == 15 for a, b in zip(time, time[1:]))
    pods = {}
    for row in raw:
        label = row['metric']
        pod = label['pod']
        rank = int(label['pp_rank'])
        vals = {int(t): int(float(v)) for t, v in row['values']}
        assert sorted(vals) == time
        assert label['tp_rank'] == '0'
        entry = pods.setdefault(pod, {'name': pod, 'suffix': pod.rsplit('-', 1)[1], 'ranks': [None] * 4})
        assert entry['ranks'][rank] is None
        entry['ranks'][rank] = [vals[t] for t in time]
    assert len(pods) == 8 and all(all(r is not None for r in p['ranks']) for p in pods.values())
    data = {
        'time': time, 'pods': [pods[key] for key in sorted(pods)],
        'summary': audit['all'], 'perPod': audit['per_pod'],
        'scrapeCheck': audit['scrape_check'], 'examples': audit['examples_pp0_lower'],
        'provenance': {
            'selector': metadata['selector'], 'startUtc': metadata['start'], 'endUtc': metadata['end'],
            'queryStepSeconds': 15, 'capturedDate': '2026-09-07',
            'rawResponseSha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            'datasource': metadata['datasource'], 'grafanaBase': metadata['base'],
            'dashboardVersion': metadata['dashboard_version'],
            'weighting': 'Equal pod/time observations. Percentages exclude observations with all four inflight gauges zero.',
        },
    }
    # Recompute the headline directly from the plotted arrays.
    strict = tied = lower = 0
    for pod in data['pods']:
        for vals in zip(*pod['ranks']):
            top = max(vals)
            if top == 0:
                continue
            if vals[0] < top:
                lower += 1
            elif vals.count(top) == 1:
                strict += 1
            else:
                tied += 1
    assert [strict, tied, lower] == [345, 1905, 595]
    encoded = json.dumps(data, separators=(',', ':'))
    (output / 'data.js').write_text('window.AUDIT = ' + encoded + ';\n')
    (output / 'evidence.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'pods': len(pods), 'samplesPerRank': len(time), 'strictTiedLower': [strict, tied, lower]}))


if __name__ == '__main__':
    main()
