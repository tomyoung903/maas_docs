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
  $('launch-equation').append(el('span','equation-label','Selected-layer reconciliation'),document.createTextNode(`${data.events.length} kernels → ${data.operator_count} operator families → ${data.groups.length} groups`));
  $('metric-scope').textContent=`${data.bound_operators} of ${data.operator_count} families have reviewed work/byte joins. Whole-layer MFU and MBU remain unavailable; “—” does not mean zero. Leaf MFU uses precision-matched nominal roofs and excludes scalar semantic operations. Estimated MBU uses useful interface-byte floors, not measured DRAM traffic; caching can make it exceed 100%.`;
  const toggles=[];
  function metric(value,label){const n=el('div','flow-metric');n.append(el('strong','',value),el('span','',label));return n;}
  function details(row){
    if(!row.work)return null;
    const d=el('details'),sum=el('summary','','Work and byte scope');d.append(sum);
    const parts=Object.entries(row.work.flops_by_precision||{}).map(([p,f])=>`${p.toUpperCase()}: ${num(f,0)} FLOPs`);
    d.append(el('p','',parts.length?parts.join(' · '):'No complete matrix/dot numerator is assigned.'));
    if(row.work.scalar_ops!=null)d.append(el('p','',`${num(row.work.scalar_ops,0)} scalar semantic operations, excluded from matrix/dot MFU.`));
    d.append(el('p','',row.work.useful_bytes_note||'No reviewed byte estimate.'));
    d.append(el('p','',`Active-union denominator: ${ms(row.union_ms)}. Physical DRAM counters are unavailable.`));
    return d;
  }
  function drawRow(row,number,color,children=[]){
    const li=el('li',`flow-step ${children.length?'inclusive is-collapsed':''}`);li.id=`row-${row.id}`;
    const body=el('div','flow-row');body.style.borderLeftColor=color;
    const heading=el('div','flow-heading'),copy=el('div','flow-copy');
    const button=children.length?el('button','flow-toggle','+'):el('span','flow-toggle-spacer');
    if(children.length){button.type='button';button.setAttribute('aria-label',`Expand ${row.title}`);button.setAttribute('aria-expanded','false');}
    heading.append(button,el('span','flow-step-id',number),copy);
    copy.append(el('div','flow-title',row.title),el('div','flow-role',row.role));
    const detail=details(row);if(detail)copy.append(detail);
    body.append(heading,metric(num(row.count,0),'launches'),metric(num(row.time_ms,3),'GPU ms'),metric(pct(row.mfu_percent),'MFU'),metric(pct(row.mbu_percent),'est. MBU'));
    li.append(body);
    if(children.length){
      const list=el('ol','flow-children');children.forEach((c,i)=>list.append(drawRow(c,`${number}.${i+1}`,color)));li.append(list);
      const set=open=>{li.classList.toggle('is-collapsed',!open);button.textContent=open?'−':'+';button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-label',`${open?'Collapse':'Expand'} ${row.title}`);};
      button.addEventListener('click',()=>set(button.getAttribute('aria-expanded')!=='true'));toggles.push({id:row.id,set});
    }
    return li;
  }
  for(const group of data.groups){
    const one=group.children.length===1;
    const row=one?{...group.children[0],id:group.id,title:group.title,role:group.role}:group;
    $('decoder-tree').append(drawRow(row,String(group.number),group.color,one?[]:group.children));
  }
  $('expand-all').addEventListener('click',()=>toggles.forEach(t=>t.set(true)));
  $('collapse-all').addEventListener('click',()=>toggles.forEach(t=>t.set(false)));
  for(const note of s.limitations)$('notes').append(el('li','',note));
  $('notes').append(el('li','',s.grouping_note));
  function evidence(label,value){$('evidence-grid').append(el('dt','',label),el('dd','mono',value));}
  evidence('Selection audit SHA-256',s.selection_audit_sha256);evidence('Complete source SHA-256',data.full_report_input_sha256);evidence('Selected event-set SHA-256',s.event_ids_sha256);
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
    for(const e of data.events){const a=(e.start_ns-data.origin_ns)/1e6,b=a+e.duration_ns/1e6;if(b<state.start||a>state.start+state.span)continue;const g=groups.get(e.group_id);ctx.fillStyle=g.color;ctx.fillRect(x(Math.max(a,state.start)),top+g.index*lane+5,Math.max(1,x(Math.min(b,state.start+state.span))-x(Math.max(a,state.start))),17);}
    $('view-range').textContent=`${num(state.start,3)}–${num(state.start+state.span,3)} ms of this layer`;
  }
  function zoom(f){const center=state.start+state.span/2;state.span*=f;constrain();state.start=center-state.span/2;draw();}
  $('zoom-in').addEventListener('click',()=>zoom(.5));$('zoom-out').addEventListener('click',()=>zoom(2));
  $('pan-left').addEventListener('click',()=>{state.start-=state.span/4;draw();});$('pan-right').addEventListener('click',()=>{state.start+=state.span/4;draw();});
  $('reset-view').addEventListener('click',()=>{state.start=0;state.span=total;draw();});
  $('timeline-title').textContent=`PP${s.rank} · layer ${s.layer} · ${data.events.length} recorded kernels`;
  canvas.addEventListener('pointerdown',e=>{state.drag={x:e.clientX,start:state.start};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointerup',e=>{state.drag=null;canvas.releasePointerCapture(e.pointerId);});canvas.addEventListener('pointercancel',()=>state.drag=null);
  canvas.addEventListener('pointermove',e=>{
    if(state.drag){state.start=state.drag.start-(e.clientX-state.drag.x)/(state.width-left-14)*state.span;draw();return;}
    const box=canvas.getBoundingClientRect(),xx=e.clientX-box.left,yy=e.clientY-box.top,index=Math.floor((yy-top)/lane);
    if(xx<left||index<0||index>=data.groups.length)return;
    const t=(state.start+(xx-left)/(state.width-left-14)*state.span)*1e6+data.origin_ns;
    const hits=data.events.filter(ev=>groups.get(ev.group_id).index===index&&ev.start_ns<=t&&ev.start_ns+ev.duration_ns>=t).sort((a,b)=>a.duration_ns-b.duration_ns);
    if(hits.length){const ev=hits[0],op=leafById.get(ev.owner_id);$('timeline-status').textContent=`${op.title} · ${num(ev.duration_ns/1e3,3)} µs · capture offset ${num(ev.start_ns/1e6,6)} ms · ${ev.id}${hits.length>1?` · ${hits.length} overlapping events`:''}`;}
    else $('timeline-status').textContent='No selected kernel at this position. Gaps are not automatically recoverable time.';
  });
  new ResizeObserver(draw).observe(canvas.parentElement);draw();
})();
