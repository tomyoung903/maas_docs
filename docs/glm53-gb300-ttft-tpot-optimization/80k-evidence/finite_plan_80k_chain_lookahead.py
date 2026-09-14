#!/usr/bin/env python3
"""Private offline real-trace planner; no network or inference operations.

Completion-touched, prefix-closed page leaf-LRU is an explicit planning model,
not a simulation of SGLang's asynchronous inclusive hierarchy. Scalar trie
edges aggregate pages with the same access time; no request bodies are read.
"""
import argparse
import collections
import hashlib
import heapq
import importlib.util
import json
from pathlib import Path
import sys
import time

HELPERS = Path('/mnt/HPC/tom/armory/environment/.codex/skills/datasets/create-custom-dataset/scripts')
sys.path.insert(0, str(HELPERS))
import select_subset as stock


class FiniteCache:
    def __init__(self, nodes, capacity, ttl=float('inf')):
        self.base = stock.PrefixCache(nodes)
        self.capacity = capacity // 64
        self.ttl = ttl
        self.paths = {}
        self.lo = [0] * len(nodes)
        self.hi = [0] * len(nodes)
        self.parent = [-1] * len(nodes)
        for i in range(1, len(nodes)):
            self.lo[i] = nodes[nodes[i]['parent']]['depth'] // 64
            self.hi[i] = nodes[i]['depth'] // 64
        self.live = [0] * len(nodes)
        self.children = [0] * len(nodes)
        self.stamp = [0] * len(nodes)
        self.access = [float('-inf')] * len(nodes)
        self.heap, self.seq, self.used, self.evicted = [], 0, 0, 0
        self.peak, self.now = 0, 0

    def path(self, node):
        if node not in self.paths:
            p = tuple(n for n in self.base.path(node) if self.hi[n] > self.lo[n])
            previous = -1
            for n in p:
                self.parent[n] = previous
                previous = n
            self.paths[node] = p
        return self.paths[node]

    def lookup(self, row):
        limit = (row['length'] - 1) // 64
        found = 0
        for n in self.path(row['node']):
            found = self.lo[n] + self.live[n]
            if found >= limit:
                return limit * 64
            if self.live[n] < self.hi[n] - self.lo[n]:
                return found * 64
        return min(found, limit) * 64

    def push(self, n):
        if n >= 0 and self.live[n] and not self.children[n]:
            heapq.heappush(self.heap, (self.access[n], self.stamp[n], n))

    def victim(self):
        while self.heap:
            t, s, n = self.heap[0]
            if self.live[n] and not self.children[n] and s == self.stamp[n]:
                return t, n
            heapq.heappop(self.heap)
        return None

    def remove(self, n, pages):
        assert 0 < pages <= self.live[n] and self.children[n] == 0
        self.live[n] -= pages
        self.used -= pages
        self.evicted += pages
        if not self.live[n]:
            parent = self.parent[n]
            if parent >= 0:
                self.children[parent] -= 1
                self.push(parent)

    def advance(self, now):
        if now < self.now - 1e-9:
            raise ValueError('cache clock went backward')
        self.now = now
        while True:
            v = self.victim()
            if v is None or v[0] >= now - self.ttl:
                break
            heapq.heappop(self.heap)
            self.remove(v[1], self.live[v[1]])

    def commit(self, row, now):
        self.advance(now)
        self.seq += 1
        for n in self.path(row['node']):
            pages = self.hi[n] - self.lo[n]
            if not self.live[n] and self.parent[n] >= 0:
                self.children[self.parent[n]] += 1
            self.used += pages - self.live[n]
            self.live[n] = pages
            self.stamp[n], self.access[n] = self.seq, now
            self.push(n)
        while self.used > self.capacity:
            _, n = self.victim()
            heapq.heappop(self.heap)
            self.remove(n, min(self.live[n], self.used - self.capacity))
            self.push(n)
        self.peak = max(self.peak, self.used)
        if len(self.heap) > 200000:
            self.heap = [(self.access[n], self.stamp[n], n) for n in range(len(self.live))
                         if self.live[n] and not self.children[n]]
            heapq.heapify(self.heap)

    def unique_tokens(self):
        return self.used * 64


def select(data, args):
    byid, parents, sessions, excluded = stock.prepare(data, args)
    future_mean={}
    for q in sessions.values():
        rr=list(q)
        for i,r in enumerate(rr):
            look=rr[i:i+8];future_mean[r['request_id']]=sum(v['length'] for v in look)/len(look)
    ideal = stock.PrefixCache(data['nodes'])
    finite = FiniteCache(data['nodes'], args.capacity_tokens, args.reuse_ttl_s)
    selected, offsets, last_session, warmed = set(), {}, {}, set()
    warm, measured, windows = [], [], []
    remaining = {s: sum(r['length'] for r in q) for s, q in sessions.items()}
    warm_tokens = 0
    commits = []

    def eligible(r):
        return all(p in selected for p in parents[r['request_id']])

    def take(s, t, dest):
        r = sessions[s].popleft()
        h, f = ideal.lookup(r), finite.lookup(r)
        assert f == h, 'only ready and retained prefixes may supply the planned ideal reuse'
        out = {k: r[k] for k in ('request_id', 'session_id', 'source_index', 'length', 'node')}
        out.update(offset_s=t, planned_offset_s=t, phase='warmup' if t is None else 'measured',
                   minute_index=None if t is None else int(t // 60),
                   ideal_cached_tokens=h, ideal_uncached_tokens=r['length'] - h,
                   finite_cached_tokens=f, finite_uncached_tokens=r['length'] - f)
        dest.append(out)
        selected.add(r['request_id'])
        offsets[r['request_id']] = t
        if t is not None:
            last_session[s] = t
        remaining[s] -= r['length']
        ideal.commit(r)
        if t is None:
            finite.commit(r, args.warmup_completion_span_s*(len(warm)-1)/max(1,args.warmup_sessions-1))
        elif args.commit_delay_s == 0:
            finite.commit(r, t+args.warmup_completion_span_s)
        else:
            heapq.heappush(commits,(t+args.warmup_completion_span_s+args.commit_delay_s,r['source_index'],r))
        return out

    order = sorted(sessions, key=lambda s: (-remaining[s], sessions[s][0]['source_index']))
    for s in order:
        if len(warm) >= args.warmup_sessions:
            break
        if len(sessions[s]) < 2 or not eligible(sessions[s][0]):
            continue
        depth=0
        while sessions[s] and len(warm) < args.warmup_sessions:
            head=sessions[s][0]
            if not eligible(head) or warm_tokens+head['length']>args.warmup_max_tokens:
                break
            r=take(s,None,warm)
            warm_tokens+=r['length'];warmed.add(s);depth+=1
            if r['length']>=100000 or depth>=3:
                break
    warm_unique = finite.unique_tokens()

    for minute in range(args.minutes):
        pending = collections.deque(sorted((s for s in sessions if sessions[s]),
            key=lambda s: (s not in warmed, -remaining[s], sessions[s][0]['source_index'])))
        pool, counts, pt, ut, start = [], collections.Counter(), 0, 0, len(measured)
        prior_uncached = sum(row['finite_uncached_tokens'] for row in measured)
        while pending and len(pool) < args.candidate_sessions:
            pool.append(pending.popleft())
        while pool and pt < args.prompt_tpm:
            now = minute * 60 + 60 * pt / args.prompt_tpm
            cache_now = now + args.warmup_completion_span_s
            while commits and commits[0][0] <= cache_now:
                done_at,_,done = heapq.heappop(commits)
                finite.commit(done,done_at)
            finite.advance(cache_now)
            best = None
            largest_miss = 0
            desired = max(0, args.uncached_tpm - ut) / max(1, args.prompt_tpm - pt)
            for s in pool:
                if not sessions[s]:
                    continue
                r = sessions[s][0]
                n = r['length']
                if not eligible(r) or pt + n > args.prompt_tpm * (1 + args.prompt_tolerance):
                    continue
                if now - last_session.get(s, -1e30) < args.min_session_gap_s:
                    continue
                if any(offsets.get(p) is not None and now - offsets[p] < args.min_session_gap_s
                       for p in parents[r['request_id']]):
                    continue
                if counts[s] + n > args.prompt_tpm * args.max_session_share:
                    continue
                h = finite.lookup(r)
                if h != ideal.lookup(r):
                    continue
                u = n - h
                if u > args.max_request_uncached_tokens or ut + u > args.uncached_tpm * (1 + args.uncached_tolerance):
                    continue
                largest_miss = max(largest_miss, u / n)
                cumulative_debt = prior_uncached + ut + u - args.uncached_tpm * (minute + (pt+n)/args.prompt_tpm)
                if abs(cumulative_debt) > 100000:
                    continue
                request_debt = (len(measured) + 1) - (minute + (pt+n)/args.prompt_tpm) * args.prompt_tpm / args.target_mean_prompt_tokens
                if abs(request_debt) > args.max_request_count_debt:
                    continue
                score = abs(cumulative_debt) / 100000
                score += 2.0 * abs(request_debt) / args.max_request_count_debt
                score += .12 * counts[s] / (args.prompt_tpm * args.max_session_share)
                if len(counts) < args.min_sessions and s not in counts:
                    score -= .15
                score -= .02 * n / args.max_prompt_tokens
                score -= .5 * max(-1.0,min(1.0,future_mean[r['request_id']]/args.target_mean_prompt_tokens-1))
                key = score, r['source_index'], s
                if best is None or key < best[0]:
                    best = key, s
            if pending and pt < args.prompt_tpm * .97 and desired > largest_miss + .03:
                pool.extend(pending.popleft() for _ in range(min(32, len(pending))))
                continue
            if best is None:
                if pending:
                    pool.extend(pending.popleft() for _ in range(min(args.candidate_sessions, len(pending))))
                    continue
                reasons = collections.Counter()
                for ss, qq in sessions.items():
                    if not qq: continue
                    rr=qq[0]; nn=rr['length']; hh=finite.lookup(rr); uu=nn-hh
                    if not eligible(rr): reasons['missing_parent']+=1
                    elif now-last_session.get(ss,-1e30)<args.min_session_gap_s: reasons['session_gap']+=1
                    elif hh!=ideal.lookup(rr): reasons['unready_or_evicted_prefix']+=1
                    elif uu>args.max_request_uncached_tokens: reasons['request_uncached_cap']+=1
                    elif abs(prior_uncached+ut+uu-args.uncached_tpm*(minute+(pt+nn)/args.prompt_tpm))>100000: reasons['uncached_debt']+=1
                    elif abs((len(measured)+1)-(minute+(pt+nn)/args.prompt_tpm)*args.prompt_tpm/args.target_mean_prompt_tokens)>args.max_request_count_debt: reasons['count_debt']+=1
                    else: reasons['remaining_other_constraints']+=1
                print(json.dumps({'frontier_exhausted_at':now,'candidate_failures':dict(reasons),'prompt_so_far':pt,'uncached_so_far':ut}),flush=True)
                break
            s = best[1]
            r = take(s, now, measured)
            pt += r['length']
            ut += r['finite_uncached_tokens']
            counts[s] += r['length']
            if not sessions[s] or counts[s] >= args.prompt_tpm * args.max_session_share - 64:
                pool.remove(s)
                if pending:
                    pool.append(pending.popleft())
        reasons = []
        if abs(pt - args.prompt_tpm) > args.prompt_tpm * args.prompt_tolerance:
            reasons.append('prompt_target_not_met')
        if abs(ut - args.uncached_tpm) > args.uncached_tpm * args.uncached_tolerance:
            reasons.append('uncached_target_not_met')
        if len(counts) < args.min_sessions:
            reasons.append('insufficient_session_diversity')
        window = dict(minute=minute, requests=len(measured)-start, prompt_tokens=pt,
                      uncached_tokens=ut, cached_tokens=pt-ut,
                      token_weighted_hit_ratio=(pt-ut)/pt if pt else None,
                      sessions=len(counts), max_session_token_share=max(counts.values(), default=0)/max(1,pt),
                      finite_resident_tokens=finite.unique_tokens(),
                      unique_prefix_tokens_committed_total=ideal.unique_tokens(),
                      passed=not reasons, failure_reasons=reasons)
        windows.append(window)
        print(json.dumps({'minute': minute, 'prompt': pt, 'uncached': ut, 'sessions': len(counts),
                          'resident': finite.unique_tokens(), 'passed': not reasons}), flush=True)
        if reasons:
            # Bounded search: preserve the failure rather than forging later bins.
            break
    validation = stock.validate(data, byid, parents, warm, measured, args)
    rolling = stock.rolling_audit([{**r,'ideal_uncached_tokens':r['finite_uncached_tokens']}
                                  for r in measured], args)
    p = sum(r['length'] for r in measured)
    u = sum(r['finite_uncached_tokens'] for r in measured)
    iu = sum(r['ideal_uncached_tokens'] for r in measured)
    passed = (len(windows) == args.minutes and validation['passed'] and
              all(w['passed'] for w in windows) and all(w['passed'] for w in rolling))
    return dict(schema='real-trace-subset-ideal/v1', source=data['source'],
        status='candidate_passed_ideal_checks' if passed else 'partial_or_failed_candidate',
        parameters=vars(args), warmup_requests=warm, measured_requests=measured,
        warmup_prompt_tokens=warm_tokens, warmup_unique_committed_prefix_tokens=warm_unique,
        windows=windows, rolling_60s_windows_every_5s=rolling, validation=validation,
        assumptions=dict(cache='quotas use finite cached/uncached counters; ideal counters are separate reference values',
            finite_model='prefix-closed page leaf-LRU, completion-touched; TTL additionally expires old leaves',
            selection_capacity_tokens=args.capacity_tokens, selection_reuse_ttl_s=args.reuse_ttl_s,
            selection_commit=f'all selected measured requests commit after {args.commit_delay_s} seconds; lookups only use completed prefixes',
            warmup=f'original warmup requests finish over {args.warmup_completion_span_s} seconds before measurement; not all fresh at time zero',
            page_size=64, reserve_last_tokens=1, output_tokens_runtime_override=100,
            finite_capacity_guarantee=False, concurrent_hit_guarantee=False,
            tolerances_are_not_user_approved=True),
        summary=dict(requests=len(measured), sessions=len({r['session_id'] for r in measured}),
            prompt_tokens=p, uncached_tokens=u, finite_token_weighted_hit_ratio=(p-u)/p if p else None,
            ideal_uncached_tokens=iu, ideal_token_weighted_hit_ratio=(p-iu)/p if p else None,
            failed_minutes=[w['minute'] for w in windows if not w['passed']],
            fixed_windows_passed=len(windows)==args.minutes and all(w['passed'] for w in windows),
            rolling_windows_passed=all(w['passed'] for w in rolling),
            failed_rolling_windows=sum(not w['passed'] for w in rolling),
            excluded_counts=dict(collections.Counter(excluded.values())),
            unselected_eligible_requests=sum(len(q) for q in sessions.values()),
            finite_model_peak_resident_tokens=finite.peak*64, finite_model_evicted_tokens=finite.evicted*64))


def main():
    p = stock.parser()
    p.description = __doc__
    p.add_argument('--target-mean-prompt-tokens', type=float, required=True)
    p.add_argument('--max-request-count-debt', type=float, default=10)
    p.add_argument('--capacity-tokens', type=int, default=9252096)
    p.add_argument('--reuse-ttl-s', type=float, default=180)
    p.add_argument('--commit-delay-s', type=float, default=8)
    p.add_argument('--warmup-completion-span-s', type=float, default=120)
    args = p.parse_args()
    if not args.input or not args.output_dir:
        p.error('--input and --output-dir are required')
    if args.target_mean_prompt_tokens <= 0 or args.max_request_count_debt <= 0:
        p.error('request mix constraints must be positive')
    started = time.monotonic()
    raw = Path(args.input).read_bytes()
    result = select(json.loads(raw), args)
    result['input_sha256'] = hashlib.sha256(raw).hexdigest()
    result['planner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['planner_elapsed_s'] = time.monotonic()-started
    result['assumptions']['output_tokens_runtime_override'] = 20
    out = Path(args.output_dir)
    out.mkdir(mode=0o700, exist_ok=False)
    with (out/'candidate.json').open('x') as f:
        json.dump(result, f, indent=2)
    for name, rows in [('warmup.jsonl', result['warmup_requests']), ('schedule.jsonl', result['measured_requests'])]:
        with (out/name).open('x') as f:
            for r in rows:
                f.write(json.dumps(r)+'\n')
    print(json.dumps(dict(status=result['status'], elapsed_s=result['planner_elapsed_s'], **result['summary'])))


if __name__ == '__main__':
    main()
