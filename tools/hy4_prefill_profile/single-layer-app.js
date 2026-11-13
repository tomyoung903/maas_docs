(() => {
  'use strict';
  const data=JSON.parse(document.getElementById('selected-layer-data').textContent), s=data.selection;
  const $=id=>document.getElementById(id);
  const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const num=(v,d=3)=>v==null?'—':v.toLocaleString('en-US',{maximumFractionDigits:d});
  const ms=v=>v==null?'—':`${num(v,3)} ms`, pct=v=>v==null?'—':`${num(v,2)}%`;
  const leafById=new Map(data.groups.flatMap(g=>g.children.map(c=>[c.id,c])));
  $('hero-description').textContent=`Layer ${s.layer} (the ${s.layer+1}th layer), on PP${s.rank}, during chunk ${s.chunk+1} of a 100K-token prefill.`;
  $('hero-meta').textContent='One recorded invocation · full indexer refresh · routed and shared experts · B300';
  $('selection-description').textContent=`${num(s.new_tokens,0)} new tokens after ${num(s.context_before,0)} prior tokens, ending at context ${num(s.context_after,0)}. Layer numbers use the model source’s zero-based indices.`;
  $('selection-rationale').textContent=s.rationale;
  function card(label,value,detail){const c=el('div','metric');c.append(el('div','label',label),el('div','value',value),el('div','detail',detail));$('summary').append(c);}
  card('Selected layer',`${s.layer} · PP${s.rank}`,`Local index ${s.local_layer_index}, within this pipeline rank`);
  card('New tokens',num(s.new_tokens,0),`Chunk ${s.chunk+1} of 13`);
  card('Context after chunk',num(s.context_after,0),`${num(s.context_before,0)} tokens before this chunk`);
  card('Recorded kernels',num(data.events.length,0),`${data.operator_count} operator families`);
  card('Aggregate GPU time',ms(data.layer_metrics.summed_residency_ms),'Sum of recorded kernel durations');
  card('Kernel window',ms((data.end_ns-data.origin_ns)/1e6),'First selected start → last selected end');
  $('launch-equation').append(el('span','equation-label','Selected-layer reconciliation'),document.createTextNode(`${data.events.length} recorded kernels · ${data.operator_count} uniquely owned operator families · one selected layer`));
  const matrix=data.matrix_scope_metrics;
  $('metric-scope').textContent=matrix?`Compute MFU is ${pct(matrix.nominal_mfu_active_union_percent)} for these ${matrix.selected_events} captured events. All ${matrix.classified_families} operator families have a reviewed matrix-work classification. For each precision, divide its model matrix FLOPs by the matching nominal GPU peak; add those ideal times, then divide by the row’s active interval union. Normalization, Hadamard butterflies, rotation, conversion and selection are scalar work, so their compute MFU is not applicable. Physical DRAM bandwidth was not measured in this original capture; the separate GPU4 replay is reported below. Per-operation byte estimates count useful interfaces once; they cannot be added into a parent MBU. This is not measured SM activity or a calibrated TileSight prediction.`:`${data.bound_operators} of ${data.operator_count} families have reviewed work/byte joins. Complete compute MFU is unavailable. Compute MFU uses precision-matched nominal roofs and each row’s active interval union. Physical DRAM bandwidth was not measured in this original capture; source-derived interface bytes do not establish physical traffic. The separate GPU4 replay is reported below.`;
  const replay=data.physical_replay;
  const replayEventIds=new Set((replay?.rows||[]).map(row=>row.original_event_id));
  if(replay){
    $('physical-memory').hidden=false;
    $('physical-replay-scope').textContent=`Separate GPU${replay.hardware.physical_gpu_index} replay of real captured layer ${s.layer} inputs: ${num(s.new_tokens,0)} queries at context ${num(s.context_after,0)}. Each native kernel was collected in one NCU pass. Initial cache state was uncontrolled; cache and clock controls were disabled.`;
    for(const row of replay.rows){
      const tr=el('tr');tr.id=`physical-replay-${row.family}`;
      const title=el('th','',row.label);title.scope='row';tr.append(title);
      for(const value of [num(row.read_bytes/1e9,3),num(row.write_bytes/1e9,3),num(row.total_bytes/1e9,3),num(row.profiled_duration_ms,6),num(row.matched_bandwidth_tb_s,3),pct(row.matched_physical_mbu_percent)])tr.append(el('td','',value));
      $('physical-replay-rows').append(tr);
    }
    $('physical-replay-definition').textContent=`Physical MBU = (DRAM read + write bytes) ÷ (matched NCU duration × ${num(replay.hardware.nominal_bandwidth_roof_tb_s,1)} TB/s nominal HBM roof). GB and TB use decimal units. These counter-run times do not replace the original tree or timeline; their MFU and useful-byte MBU remain unchanged.`;
    $('physical-replay-validation').textContent=`Both chains matched all ${num(replay.numerical.valid_logits_per_chain,0)} valid MQA logits bitwise. TopK selected the same token sets with different index order. This is a native baseline observation, not FP64 candidate validation, a calibrated TileSight prediction, or an optimization gain.`;
    for(const note of replay.limitations)$('physical-replay-notes').append(el('li','',note));
  }
  const toggles=[];
  const eventById=new Map(data.events.map(event=>[event.id,event]));
  const semanticEventTitles=new Map();
  let selectedEventIds=new Set();
  const textValue=value=>{
    if(value==null)return '';
    if(Array.isArray(value))return value.map(textValue).filter(Boolean).join(' · ');
    if(typeof value==='object')return Object.entries(value).map(([k,v])=>`${k}: ${textValue(v)}`).join(' · ');
    return String(value);
  };
  const workLine=row=>{
    const flops=row.compute_work?.flops_by_precision??row.work?.flops_by_precision;
    if(flops==null)return '';
    const parts=Object.entries(flops).map(([precision,flops])=>`${precision.toUpperCase()} · ${num(flops/1e9,3)} model GFLOPs`);
    return parts.length?parts.join(' · '):'No matrix work; scalar arithmetic or data movement';
  };
  const byteLine=row=>{const bytes=row.additional_work?.useful_bytes??row.work?.useful_bytes;return bytes==null?'':`${num(bytes/1e6,3)} MB useful interface · not measured DRAM`;};
  function metric(value,label,note){
    const n=el('div','flow-metric');n.append(el('strong','',value),el('span','',label));
    if(note)n.append(el('small','',note));
    return n;
  }
  function details(row){
    const source=textValue(row.source);
    const byteNote=row.additional_work?.useful_bytes_note??row.work?.useful_bytes_note;
    const eventIds=(row.selected_event_ids||[]).filter(id=>data.event_evidence?.[id]);
    if(!source&&!byteNote&&!row.note&&!eventIds.length)return null;
    const d=el('details','row-details'),sum=el('summary','','Source and measurement scope');d.append(sum);
    if(source)d.append(el('p','mono',source));
    if(row.additional_work){
      const extra=row.additional_work;
      d.append(el('p','',`Matrix-work classification: ${extra.matrix_scope_note}`));
      for(const anchor of extra.source_anchors||[])d.append(el('p','mono',`${anchor.label}:${anchor.line} · ${anchor.anchor}`));
      if(extra.scalar_formula)d.append(el('p','',`Scalar-operation convention: ${extra.scalar_formula}. This is model arithmetic, not an executed-instruction count.`));
      if(extra.useful_byte_formula)d.append(el('p','',`Useful-byte formula: ${extra.useful_byte_formula}.`));
    }
    if(row.note)d.append(el('p','',textValue(row.note)));
    if(byteNote)d.append(el('p','',byteNote));
    d.append(el('p','',`Active-union denominator: ${ms(row.union_ms)}. Physical DRAM counters are unavailable for this original captured interval. Summed kernel duration is not isolated operator latency.`));
    if(eventIds.length===1&&replayEventIds.has(eventIds[0])){
      const line=el('p'),link=el('a','','See physical counters from the separate replay');link.href='#physical-memory';line.append(link);d.append(line);
    }
    if(eventIds.length){
      const raw=el('details','raw-kernel-evidence');raw.append(el('summary','',`${eventIds.length} raw kernel ${eventIds.length===1?'record':'records'} · symbol and launch geometry`));
      let built=false;
      raw.addEventListener('toggle',()=>{
        if(!raw.open||built)return;
        built=true;
        for(const id of eventIds){
          const info=data.event_evidence[id],event=eventById.get(id),record=el('div','raw-kernel-record');
          record.append(el('h4','',`Selected kernel #${info.selected_ordinal??'—'} · trace row ${info.sqlite_rowid??'—'}`));
          record.append(el('pre','raw-kernel-symbol',info.kernel_name||'Full symbol unavailable.'));
          const facts=el('dl','kernel-facts');
          const fact=(label,value)=>{if(value!=null&&textValue(value)!=='')facts.append(el('dt','',label),el('dd','mono',textValue(value)));};
          fact('Event ID',id);fact('Stream',info.stream_id);
          if(event)fact('Recorded duration',`${num(event.duration_ns/1e3,3)} µs`);
          for(const [key,value] of Object.entries(info.launch_geometry||{}))fact(key.replaceAll('_',' '),value);
          fact('Symbol SHA-256',info.kernel_symbol_sha256);
          record.append(facts);
          if(info.owner_evidence)record.append(el('p','',textValue(info.owner_evidence)));
          raw.append(record);
        }
      });
      d.append(raw);
    }
    return d;
  }
  function inlineEvidence(row,copy){
    const evidence=el('div','flow-evidence');
    const ordinal=textValue(row.event_ordinals||row.event_ordinal_range);
    if(ordinal)evidence.append(el('div','mono event-ordinals',`PP${s.rank} ${ordinal}`));
    const geometry=textValue(row.geometry||row.shape);
    if(geometry)evidence.append(el('div','geometry-note',geometry));
    if(row.formula)evidence.append(el('div','formula-note',textValue(row.formula)));
    const kernels=textValue(row.kernel_evidence);
    if(kernels)evidence.append(el('div','kernel-evidence',kernels));
    const work=workLine(row),mode=textValue(row.actual_mode);
    if(mode||work)evidence.append(el('div','precision-note',[mode,work].filter(Boolean).join(' · ')));
    const scalar=row.scalar_work?.known_ops??row.additional_work?.scalar_ops??row.work?.scalar_ops;
    if(scalar!=null&&scalar!==0)evidence.append(el('div','scalar-note',`${num(scalar/1e9,3)} G scalar semantic operations${row.scalar_work?.coverage_complete===false?' · partial reviewed sum':''} · excluded from compute MFU`));
    if(row.coverage_note)evidence.append(el('div','coverage-note',textValue(row.coverage_note)));
    const bytes=byteLine(row);if(bytes)evidence.append(el('div','byte-note',bytes));
    if(evidence.childElementCount)copy.append(evidence);
  }
  function drawRow(row,number,color,children=row.children||[],depth=0){
    const rawChildren=children.length>0&&children.every(c=>['kernel','event','physical_kernel','physical'].includes(c.kind));
    const open=row.default_expanded??!rawChildren;
    const li=el('li',`flow-step flow-depth-${depth} ${children.length?'inclusive':''} ${children.length&&!open?'is-collapsed':''} ${row.kind==='kernel'||row.kind==='event'?'physical-step':''}`);li.id=`row-${row.id}`;
    const body=el('div',`flow-row ${children.length?'':'is-leaf'}`);body.style.borderLeftColor=row.color||color||'#aeb7bd';
    const heading=el('div','flow-heading'),copy=el('div','flow-copy');
    const button=children.length?el('button','flow-toggle',open?'▾':'▸'):el('span','flow-toggle-spacer');
    const listId=`children-${row.id}`;
    if(children.length){button.type='button';button.setAttribute('aria-controls',listId);button.setAttribute('aria-label',`${open?'Collapse':'Expand'} ${row.title}`);button.setAttribute('aria-expanded',String(open));}
    heading.append(button,el('span','flow-step-id',row.number||number),copy);
    copy.append(el('div','flow-title',row.title),el('div','flow-role',row.role||''));
    inlineEvidence(row,copy);
    const detail=details(row);if(detail)copy.append(detail);
    const rowEventIds=(row.selected_event_ids||data.events.filter(event=>event.owner_id===row.id).map(event=>event.id)).filter(id=>eventById.has(id));
    if(rowEventIds.length){
      const locate=el('button','locate-kernels','Locate kernels');locate.type='button';locate.setAttribute('aria-label',`Locate ${rowEventIds.length} kernels for ${row.title} on the timeline`);
      locate.addEventListener('click',()=>locateKernels(row,li,rowEventIds));copy.append(locate);
    }
    const flops=row.compute_work?.flops_by_precision??row.work?.flops_by_precision;
    const completeWork=row.compute_work?.complete??(row.work_bound&&flops!=null);
    const noMatrix=completeWork&&Object.keys(flops||{}).length===0;
    const mfuValue=row.mfu_percent!=null?pct(row.mfu_percent):noMatrix?'N/A':'Unknown';
    const mfuNote=row.mfu_note||(row.mfu_percent==null?(noMatrix?'No matrix work':'Matrix-work scope incomplete'):'Precision-weighted nominal peaks · active union');
    const mbuValue=row.mbu_percent!=null?pct(row.mbu_percent):'Not measured';
    const mbuNote=row.mbu_note||(row.mbu_percent==null?(children.length?'Original-capture DRAM traffic unavailable; child interfaces cannot be added':'Original-capture DRAM traffic unavailable; useful-byte estimate unresolved'):'Useful-byte estimate · original-capture DRAM unmeasured');
    body.append(heading,metric(num(row.count,0),children.length?'inclusive launches':'launches'),metric(num(row.time_ms,3),'summed kernel ms',`union ${num(row.union_ms,3)} ms`),metric(mfuValue,'compute MFU',mfuNote),metric(mbuValue,row.mbu_percent==null?'physical MBU':'est. useful-byte MBU',mbuNote));
    li.append(body);
    if(children.length){
      const list=el('ol','flow-children');list.id=listId;children.forEach((c,i)=>list.append(drawRow(c,`${number}.${i+1}`,c.color||row.color||color,c.children||[],depth+1)));li.append(list);
      const set=expanded=>{li.classList.toggle('is-collapsed',!expanded);button.textContent=expanded?'▾':'▸';button.setAttribute('aria-expanded',String(expanded));button.setAttribute('aria-label',`${expanded?'Collapse':'Expand'} ${row.title}`);};
      button.addEventListener('click',()=>set(button.getAttribute('aria-expanded')!=='true'));toggles.push({id:row.id,set});
    }
    return li;
  }
  const trees=data.tree?(Array.isArray(data.tree)?data.tree:[data.tree]):data.groups;
  for(const [index,row] of trees.entries())$('decoder-tree').append(drawRow(row,String(row.number||index+1),row.color,row.children||[]));
  const logicalLeaves=[];
  function collectLeaves(row){
    if(row.children?.length){row.children.forEach(collectLeaves);return;}
    logicalLeaves.push(row);
    for(const id of row.selected_event_ids||[])semanticEventTitles.set(id,row.title);
  }
  trees.forEach(collectLeaves);
  if($('reading-costs')){
    const largest=logicalLeaves.filter(row=>Number.isFinite(row.time_ms)&&row.count>0).sort((a,b)=>b.time_ms-a.time_ms).slice(0,3);
    $('reading-costs').append(el('strong','','Largest recorded durations: '));
    const line=el('span');
    for(const [index,row] of largest.entries()){
      if(index)line.append(document.createTextNode(' · '));
      const link=el('a','',`${row.title}: ${ms(row.time_ms)}`);link.href=`#row-${row.id}`;line.append(link);
    }
    $('reading-costs').append(line,el('small','','These are summed captured kernel durations, not isolated latency or a prediction of removable time.'));
  }
  $('expand-all').addEventListener('click',()=>toggles.forEach(t=>t.set(true)));
  $('collapse-all').addEventListener('click',()=>toggles.forEach(t=>t.set(false)));
  if($('tree-legend')){
    for(const [label,cls] of [['Inclusive subtotal','inclusive'],['Indexer refresh','refresh'],['Routed / shared MoE','moe']]){const item=el('span'),swatch=el('i',cls);item.append(swatch,document.createTextNode(label));$('tree-legend').append(item);}
    $('tree-legend').append(el('span','precision-key','Model GFLOPs by precision · scalar work separate'),el('span','formula-key','T = 8,192 · H = 6,144 · C/S = useful pairs'));
  }
  for(const note of s.limitations)$('notes').append(el('li','',note));
  $('notes').append(el('li','',s.grouping_note));
  function evidence(label,value){$('evidence-grid').append(el('dt','',label),el('dd','mono',value));}
  evidence('Selection audit SHA-256',s.selection_audit_sha256);evidence('Complete source SHA-256',data.full_report_input_sha256);evidence('Selected event-set SHA-256',s.event_ids_sha256);
  if(data.metric_completion_evidence){
    evidence('Metric completion evidence SHA-256',data.metric_completion_evidence.evidence_sha256);
    for(const pin of data.metric_completion_evidence.source_pins)evidence(pin.label,pin.sha256);
    for(const note of data.metric_completion_evidence.limits)$('notes').append(el('li','',note));
  }
  for(const a of data.artifacts)evidence(a.label,a.sha256);
  const request=data.request_context;
  $('request-context').textContent=`Full capture context: ${num(request.input_tokens,0)} cold input tokens; server prefill ${ms(request.server_prefill_ms)}; client wall ${ms(request.client_wall_ms)}. Whole-request useful target-model MFU ${pct(request.target_model_mfu_percent)} is a separate quantity, not this layer’s MFU.`;

  // A small measured timeline, limited to the selected 45 events.
  const canvas=$('timeline'),ctx=canvas.getContext('2d'),total=(data.end_ns-data.origin_ns)/1e6;
  const state={start:0,span:total,width:1000,drag:null};
  const groups=new Map(data.groups.map((g,i)=>[g.id,{...g,index:i}]));
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  let left=250,top=32,lane=31;
  function constrain(){state.span=clamp(state.span,total/64,total);state.start=clamp(state.start,0,total-state.span);}
  function x(t){return left+(t-state.start)/state.span*(state.width-left-14);}
  function draw(){
    constrain();state.width=Math.max(320,canvas.parentElement.clientWidth);left=state.width<650?145:250;
    const height=top+data.groups.length*lane+18,dpr=window.devicePixelRatio||1;
    canvas.width=Math.round(state.width*dpr);canvas.height=Math.round(height*dpr);canvas.style.width=`${state.width}px`;canvas.style.height=`${height}px`;
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,state.width,height);ctx.font='11px system-ui';ctx.textBaseline='middle';
    for(let i=0;i<=5;i++){const t=state.start+state.span*i/5,xx=x(t);ctx.strokeStyle='#e0e5e8';ctx.beginPath();ctx.moveTo(xx,top-10);ctx.lineTo(xx,height-9);ctx.stroke();ctx.fillStyle='#626a73';ctx.textAlign=i===5?'right':'left';ctx.fillText(`${num(t,2)} ms`,xx,13);}
    ctx.textAlign='left';
    for(const g of groups.values()){
      const y=top+g.index*lane;ctx.fillStyle=g.index%2?'#f6f8f9':'#fff';ctx.fillRect(left,y,state.width-left-14,lane-3);ctx.fillStyle=g.color;
      const max=left===145?18:36,label=`${g.number}. ${g.title}`;ctx.fillText(label.length>max?label.slice(0,max-1)+'…':label,8,y+13);
    }
    for(const e of data.events){
      const a=(e.start_ns-data.origin_ns)/1e6,b=a+e.duration_ns/1e6;if(b<state.start||a>state.start+state.span)continue;
      const g=groups.get(e.group_id),selected=selectedEventIds.has(e.id),xx=x(Math.max(a,state.start)),yy=top+g.index*lane+5,width=Math.max(1,x(Math.min(b,state.start+state.span))-xx);
      ctx.globalAlpha=selectedEventIds.size&&!selected ? .2 : 1;ctx.fillStyle=g.color;ctx.fillRect(xx,yy,width,17);
      if(selected){ctx.strokeStyle='#202428';ctx.lineWidth=1.5;ctx.strokeRect(xx,yy,width,17);}
      ctx.globalAlpha=1;
    }
    $('view-range').textContent=`${num(state.start,3)}–${num(state.start+state.span,3)} ms of this layer`;
  }
  function locateKernels(row,li,ids){
    selectedEventIds=new Set(ids);
    for(const item of document.querySelectorAll('.row-highlight'))item.classList.remove('row-highlight');
    li.classList.add('row-highlight');
    const events=ids.map(id=>eventById.get(id)),start=(Math.min(...events.map(event=>event.start_ns))-data.origin_ns)/1e6,end=(Math.max(...events.map(event=>event.start_ns+event.duration_ns))-data.origin_ns)/1e6;
    const padding=Math.max((end-start)*.08,total/256);
    state.start=start-padding;state.span=end-start+2*padding;draw();
    $('timeline-status').textContent=`${row.title} · ${ids.length} exact ${ids.length===1?'kernel':'kernels'} highlighted · ${num(start,6)}–${num(end,6)} ms from this layer’s first kernel.`;
    $('timeline-section').scrollIntoView({behavior:'smooth',block:'start'});
  }
  function zoom(f){const center=state.start+state.span/2;state.span*=f;constrain();state.start=center-state.span/2;draw();}
  $('zoom-in').addEventListener('click',()=>zoom(.5));$('zoom-out').addEventListener('click',()=>zoom(2));
  $('pan-left').addEventListener('click',()=>{state.start-=state.span/4;draw();});$('pan-right').addEventListener('click',()=>{state.start+=state.span/4;draw();});
  $('reset-view').addEventListener('click',()=>{state.start=0;state.span=total;selectedEventIds.clear();for(const item of document.querySelectorAll('.row-highlight'))item.classList.remove('row-highlight');$('timeline-status').textContent='Hover a kernel to inspect it.';draw();});
  $('timeline-title').textContent=`PP${s.rank} · layer ${s.layer} · ${data.events.length} recorded kernels`;
  canvas.addEventListener('pointerdown',e=>{state.drag={x:e.clientX,start:state.start};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointerup',e=>{state.drag=null;canvas.releasePointerCapture(e.pointerId);});canvas.addEventListener('pointercancel',()=>state.drag=null);
  canvas.addEventListener('pointermove',e=>{
    if(state.drag){state.start=state.drag.start-(e.clientX-state.drag.x)/(state.width-left-14)*state.span;draw();return;}
    const box=canvas.getBoundingClientRect(),xx=e.clientX-box.left,yy=e.clientY-box.top,index=Math.floor((yy-top)/lane);
    if(xx<left||index<0||index>=data.groups.length)return;
    const t=(state.start+(xx-left)/(state.width-left-14)*state.span)*1e6+data.origin_ns;
    const hits=data.events.filter(ev=>groups.get(ev.group_id).index===index&&ev.start_ns<=t&&ev.start_ns+ev.duration_ns>=t).sort((a,b)=>a.duration_ns-b.duration_ns);
    if(hits.length){const ev=hits[0],op=leafById.get(ev.owner_id);$('timeline-status').textContent=`${semanticEventTitles.get(ev.id)||op?.title||'Recorded kernel'} · ${num(ev.duration_ns/1e3,3)} µs · capture offset ${num(ev.start_ns/1e6,6)} ms · ${ev.id}${hits.length>1?` · ${hits.length} overlapping events`:''}`;}
    else $('timeline-status').textContent='No selected kernel at this position. Gaps are not automatically recoverable time.';
  });
  new ResizeObserver(draw).observe(canvas.parentElement);draw();
})();
