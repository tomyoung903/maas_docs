(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('report-data').textContent);
  const byId = new Map(data.nodes.map(n => [n.id, n]));
  const metrics = data.derived.nodes;
  const $ = id => document.getElementById(id);
  const el = (tag, cls, text) => { const e=document.createElement(tag); if(cls)e.className=cls; if(text!==undefined)e.textContent=text; return e; };
  const num = (x, digits=3) => x===null || x===undefined ? '—' : x.toLocaleString('en-US',{maximumFractionDigits:digits});
  const ms = x => x===null ? '—' : `${num(x)} ms`;
  const pct = x => x===null ? '—' : `${num(x,2)}%`;
  const work = x => { const v=Number(x); for(const [s,u] of [[1e15,'PFLOP'],[1e12,'TFLOP'],[1e9,'GFLOP'],[1e6,'MFLOP']]) if(v>=s)return `${num(v/s,4)} ${u}`; return `${num(v)} FLOP`; };
  const bytes = x => x===null ? '—' : x>=1e9 ? `${num(x/1e9,3)} GB` : `${num(x/1e6,3)} MB`;
  const names={nvfp4:'NVFP4 Tensor Core',fp8:'FP8 Tensor Core',bf16:'BF16 Tensor Core',fp16:'FP16 Tensor Core',tf32:'TF32 Tensor Core',fp32:'FP32 SIMT',fp64:'FP64'};
  const pending=data.status==='pending';
  $('status').append(el('div',`banner ${pending?'':'measured'}`,pending ? 'Measurement pending. The tree below is a source-based logical inventory. No 100K request timing, measured coldness, chunk schedule or utilization is claimed.' : 'Measured request. Timings are observed GPU intervals; work and useful-byte values remain explicitly modeled unless matched to this execution.'));
  function card(label,value,note){const c=el('div','card');c.append(el('div','label',label),el('div','value',value),el('small','',note));$('summary').append(c);}
  card('Profiled server prefill',ms(data.request.profiled_server_prefill_ms??null),'Server forward-entry → prefill-finished interval');
  card('Profiled client wall time',ms(data.request.wall_time_ms),'Full request including protocol overhead; request MFU denominator');
  card('GPU summed residency',ms(data.derived.all_events_residency_ms),'Sum over all four ranks, including unattributed events');
  card('GPU active union',ms(data.derived.all_events_device_union_sum_ms),'Sum of four independent device unions');
  card('Whole-request target-model MFU',pct(data.derived.target_model_request_mfu_percent),'Useful target-model matrix/dot work ÷ nominal capacity over 4 × client wall time');
  card('Captured GPU events',num(data.derived.total_event_count,0),'Kernels, copies and memsets across four pipeline ranks');
  $('configuration').textContent=`Baseline: PP ${data.request.layer_partition.join('/')} · ${data.request.input_tokens.toLocaleString()} input tokens · ${data.request.output_tokens} output token · ${data.request.configuration}`;
  if(data.request.warmup_server_prefill_ms!=null){$('warmup-note').hidden=false;$('warmup-note').textContent=`Preparation call: ${ms(data.request.warmup_server_prefill_ms)} server prefill. This separate warmup call is not the profiled request or a comparison baseline. The timeline and operator measurements below describe one profiled request.`;}
  if(data.target_model_work){$('target-scope').hidden=false;$('target-scope').textContent=`Whole-request MFU numerator: ${data.target_model_work.scope} Its client-wall denominator includes auxiliary, draft and idle overhead. It does not require every trace event to have an operator owner and does not measure issued instruction utilization.`;}
  for(const rank of data.hardware.devices){const o=el('option','',`PP${rank}`);o.value=String(rank);$('rank-filter').append(o);}
  const chunks = [...new Set(data.nodes.filter(n=>n.kind==='chunk').map(n=>String(n.chunk)))];
  for(const chunk of chunks){const o=el('option','',chunk==='pending'?'Schedule pending':`Chunk ${chunk}`);o.value=chunk;$('chunk-filter').append(o);}
  let rankFilter='all',chunkFilter='all';
  function included(n){if(n.kind==='model')return true;if(rankFilter!=='all'&&String(n.rank)!==rankFilter)return false;if(['chunk','layer','operator'].includes(n.kind)&&chunkFilter!=='all'&&String(n.chunk)!==chunkFilter)return false;return true;}
  function metricCell(label){const c=el('div','metric');c.append(el('span','metric-label',label));return c;}
  function drawNode(id){
    const n=byId.get(id); if(!included(n))return null;
    const m=metrics[id], kids=data.derived.children[id].filter(x=>included(byId.get(x)));
    const li=el('li','tree-node');li.dataset.kind=n.kind;li.dataset.nodeId=id;
    const row=el('div','tree-row'),title=el('div','title-wrap'),label=el('div');
    const button=el('button','toggle',kids.length?'▸':'·');button.type='button';button.disabled=!kids.length;
    button.setAttribute('aria-label',`Expand ${n.label}`);button.setAttribute('aria-expanded','false');
    title.append(button,label);label.append(el('div','node-title',n.label));
    label.append(el('div','node-subtitle',n.kind==='operator' ? (n.work.status==='source_estimate'?'Source estimate':n.work.status) : n.kind==='model'?'Attributed events only; totals do not change with filters':n.note||n.kind));
    const times=metricCell('Observed owned GPU time');times.append(el('div','',`Residency ${ms(m.summed_residency_ms)}`),el('div','',`${n.kind==='model'?'Σ device unions':'Active union'} ${ms(m.device_union_sum_ms)}`),el('small','',`${num(m.event_count,0)} GPU events`));
    if(m.event_kind_counts)times.append(el('small','',`${num(m.event_kind_counts.kernel,0)} kernels · ${num(m.event_kind_counts.memcpy,0)} copies · ${num(m.event_kind_counts.memset,0)} memsets`));
    if(n.kind==='rank' && data.derived.unattributed_by_rank){const u=data.derived.unattributed_by_rank[String(n.rank)];if(u.event_count)times.append(el('small','unknown',`Plus ${num(u.event_count,0)} unattributed events (${ms(u.residency_ms)})`));}
    const flops=metricCell('Logical matrix / dot work');
    const entries=Object.entries(m.flops_by_precision);
    if(!entries.length)flops.append(el('div','unknown',m.flop_coverage_complete?'No matrix/dot FLOPs':'—'));
    for(const [p,f] of entries){const a=el('span','precision',`${p.toUpperCase()}: ${work(f)}`);a.title=`${names[p]||p}: ${m.flops_by_precision_exact[p]} FLOP`;flops.append(a);}
    if(!m.flop_coverage_complete)flops.append(el('small','unknown',`Partial: ${m.leaves_with_flops}/${m.operator_leaves} leaves have a work model`));
    if(n.work.scalar_ops!==null)flops.append(el('small','',`${num(n.work.scalar_ops,0)} scalar semantic ops; separate`));
    const util=metricCell('MFU · matrix/dot model fraction');util.append(el('div','',`${pct(m.mfu_active_union_percent)} / active union`),el('small','',`${pct(m.mfu_summed_residency_percent)} / summed residency`));
    util.append(el('div','',`Useful-byte MBU ${pct(m.estimated_mbu_active_union_percent)}`),el('small','',`Useful interface ${bytes(m.useful_bytes)}; / active union`),el('div','',`DRAM-counter MBU ${pct(m.counter_mbu_active_union_percent)}`));
    row.append(title,times,flops,util);
    if(n.kind==='operator'){
      const note=el('div','node-note');
      note.textContent=[n.formula?`Work: ${n.formula}`:'',n.note||'',n.work.useful_bytes_note||'',!n.work_matches_events?'Work-to-event correspondence not yet verified.':''].filter(Boolean).join(' ');
      row.append(note);
    }
    li.append(row);let list=null;
    function open(){if(!kids.length)return;if(!list){list=el('ol','tree-list');for(const kid of kids){const child=drawNode(kid);if(child)list.append(child);}li.append(list);}list.hidden=false;button.textContent='▾';button.setAttribute('aria-expanded','true');button.setAttribute('aria-label',`Collapse ${n.label}`);}
    function close(){if(list)list.hidden=true;button.textContent='▸';button.setAttribute('aria-expanded','false');button.setAttribute('aria-label',`Expand ${n.label}`);}
    button.addEventListener('click',()=>button.getAttribute('aria-expanded')==='true'?close():open());
    li._open=open;li._close=close;
    if(n.kind==='model')open();
    return li;
  }
  function render(){const tree=el('ol','tree-list');tree.append(drawNode(data.derived.root_id));$('tree').replaceChildren(tree);}
  $('rank-filter').addEventListener('change',e=>{rankFilter=e.target.value;render();});
  $('chunk-filter').addEventListener('change',e=>{chunkFilter=e.target.value;render();});
  $('expand-one').addEventListener('click',()=>{const closed=[...$('tree').querySelectorAll('.tree-node')].filter(n=>!n.closest('[hidden]')&&n.querySelector(':scope > .tree-row .toggle').getAttribute('aria-expanded')==='false');for(const n of closed)n._open();});
  $('collapse').addEventListener('click',()=>{for(const n of $('tree').querySelectorAll('.tree-node'))if(n.dataset.kind!=='model')n._close();});
  render();
  HY4Timeline.mount(data);
  $('coverage-body').append(el('p','muted',pending?'No GPU event ledger has been imported. Source estimates have no measured latency denominator.':`${num(data.derived.unattributed_event_count,0)} of ${num(data.derived.total_event_count,0)} events remain unattributed (${ms(data.derived.unattributed_residency_ms)} residency). Unattributed events remain in full-GPU summaries and block the fully event-bound request metric.`));
  if(!pending)$('coverage-body').append(el('p','muted',`Fully event-bound request MFU: ${pct(data.derived.request_mfu_percent)}. This stricter quantity requires complete trace/work joins and remains separate from useful target-model MFU.`));
  for(const text of data.limitations)$('limitations').append(el('li','',text));
  $('input-hash').textContent=`Normalized input SHA-256: ${data.input_sha256}`;
  for(const a of data.artifacts){const item=el('div','artifact');item.append(el('strong','',a.label),el('div','hash',`SHA-256 ${a.sha256}`));if(a.url){const link=el('a','',a.url);link.href=a.url;link.rel='noreferrer';item.append(link);}$('artifact-list').append(item);}
  for(const s of data.generator_sources)$('generator-hashes').append(el('div','hash',`${s.label}: ${s.sha256}`));
})();
