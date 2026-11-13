/* Measured intervals only. Pure math helpers are also exercised in Node tests. */
const HY4Timeline = (() => {
  'use strict';
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  const colors={compute:'#0b756c',communication:'#c77723',memory:'#7163ad',unclassified:'#89958e'};
  const track={compute:25,communication:43,memory:57,unclassified:70};
  function category(e){return e.category || (e.kind==='memcpy'||e.kind==='memset'?'memory':e.owner_id?'compute':'unclassified');}
  function windowFor(domain,zoom,position){const total=domain[1]-domain[0];const span=total/Math.max(1,zoom);const start=domain[0]+clamp(position,0,1)*(total-span);return [start,start+span];}
  function xFor(time,range,width,left=68){return left+(time-range[0])/(range[1]-range[0])*(width-left-14);}
  function hits(events,rank,time,tolerance=0){return events.filter(e=>e.rank===rank&&e.start_ns<=time+tolerance&&e.start_ns+e.duration_ns>=time-tolerance).sort((a,b)=>a.duration_ns-b.duration_ns||a.start_ns-b.start_ns);}
  function scene(data){
    const info=data.derived.timeline;
    if(!info?.available)return {available:false,reason:info?.reason||'Common-clock evidence is unavailable.'};
    return {available:true,domain:[info.start_ns,info.end_ns],events:data.events,chunks:data.timeline.chunks};
  }
  function mount(data){
    const $=id=>document.getElementById(id),s=scene(data),status=$('timeline-status'),canvas=$('timeline-canvas'),controls=$('timeline-controls'),hover=$('timeline-hover');
    if(!s.available){status.textContent=data.status==='pending'?'Measurement pending. No GPU intervals are available to draw.':`Shared-axis timeline unavailable: ${s.reason}`;canvas.hidden=true;controls.hidden=true;hover.hidden=true;return;}
    status.textContent='All four lanes use the same captured Nsight clock. Time zero is the retained capture origin; ranks have not been shifted independently. Shaded spans are correlated forward windows, not sums of kernel durations.';
    canvas.hidden=false;controls.hidden=false;hover.hidden=false;
    const byId=new Map(data.nodes.map(n=>[n.id,n]));
    const state={zoom:1,start:s.domain[0],span:s.domain[1]-s.domain[0],width:1000,drag:null};
    const total=s.domain[1]-s.domain[0],ctx=canvas.getContext('2d'),height=398,left=68,top=35,lane=86;
    const format=(x,d=3)=>x.toLocaleString('en-US',{maximumFractionDigits:d});
    function range(){return [state.start,state.start+state.span];}
    function sync(){const maxStart=s.domain[1]-state.span;state.start=clamp(state.start,s.domain[0],maxStart);$('timeline-pan').value=String(total>state.span?(state.start-s.domain[0])/(total-state.span)*10000:0);$('timeline-pan').disabled=state.zoom===1;$('timeline-window').textContent=`${format(state.start/1e6)}–${format((state.start+state.span)/1e6)} ms · ${state.zoom}×`;}
    function draw(){
      state.width=Math.max(320,canvas.parentElement.clientWidth);const dpr=window.devicePixelRatio||1;canvas.width=Math.round(state.width*dpr);canvas.height=Math.round(height*dpr);canvas.style.width=`${state.width}px`;canvas.style.height=`${height}px`;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,state.width,height);ctx.fillStyle='#fff';ctx.fillRect(0,0,state.width,height);ctx.font='11px system-ui';ctx.textBaseline='middle';const r=range();
      for(let i=0;i<=6;i++){const t=r[0]+state.span*i/6,x=xFor(t,r,state.width);ctx.strokeStyle='#e2e9e5';ctx.beginPath();ctx.moveTo(x,top-9);ctx.lineTo(x,height-15);ctx.stroke();ctx.fillStyle='#596865';ctx.textAlign=i===6?'right':'left';ctx.fillText(`${format(t/1e6,2)} ms`,x,14);}
      ctx.textAlign='left';
      for(let rank=0;rank<4;rank++){const y=top+rank*lane;ctx.fillStyle=rank%2?'#f7faf8':'#fcfdfc';ctx.fillRect(left,y,state.width-left-14,lane-4);ctx.fillStyle='#18211f';ctx.font='bold 12px system-ui';ctx.fillText(`PP${rank}`,9,y+39);ctx.font='10px system-ui';
        for(const c of s.chunks.filter(x=>x.rank===rank&&x.start_ns<r[1]&&x.start_ns+x.duration_ns>r[0])){const x1=xFor(Math.max(c.start_ns,r[0]),r,state.width),x2=xFor(Math.min(c.start_ns+c.duration_ns,r[1]),r,state.width);ctx.fillStyle=c.forward_ordinal%2?'rgba(11,107,102,.045)':'rgba(11,107,102,.085)';ctx.fillRect(x1,y,x2-x1,lane-4);ctx.strokeStyle='#aec8ba';ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(x1,y);ctx.lineTo(x1,y+lane-4);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#526d60';if(x2-x1>37)ctx.fillText(`F${c.forward_ordinal+1}${x2-x1>140&&c.new_tokens!==null?' · '+format(c.new_tokens,0)+' tokens':''}`,x1+3,y+9);}
        for(const e of s.events){if(e.rank!==rank||e.start_ns>=r[1]||e.start_ns+e.duration_ns<=r[0])continue;const kind=category(e),x1=xFor(Math.max(e.start_ns,r[0]),r,state.width),x2=xFor(Math.min(e.start_ns+e.duration_ns,r[1]),r,state.width);ctx.fillStyle=colors[kind];ctx.fillRect(x1,y+track[kind],Math.max(1,x2-x1),kind==='compute'?14:8);}
        ctx.strokeStyle='#c9d6d2';ctx.beginPath();ctx.moveTo(left,y+lane-3);ctx.lineTo(state.width-14,y+lane-3);ctx.stroke();
      }
      sync();
    }
    function zoom(direction){const center=state.start+state.span/2;state.zoom=clamp(state.zoom*(direction>0?2:.5),1,1024);state.span=total/state.zoom;state.start=center-state.span/2;sync();draw();}
    $('timeline-zoom-in').addEventListener('click',()=>zoom(1));$('timeline-zoom-out').addEventListener('click',()=>zoom(-1));
    $('timeline-reset').addEventListener('click',()=>{state.zoom=1;state.start=s.domain[0];state.span=total;draw();});
    $('timeline-left').addEventListener('click',()=>{state.start-=state.span/4;sync();draw();});$('timeline-right').addEventListener('click',()=>{state.start+=state.span/4;sync();draw();});
    $('timeline-pan').addEventListener('input',e=>{state.start=s.domain[0]+Number(e.target.value)/10000*(total-state.span);draw();});
    canvas.addEventListener('pointerdown',e=>{state.drag={x:e.clientX,start:state.start};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointerup',e=>{state.drag=null;canvas.releasePointerCapture(e.pointerId);});canvas.addEventListener('pointercancel',()=>{state.drag=null;});
    canvas.addEventListener('pointermove',e=>{const box=canvas.getBoundingClientRect(),x=e.clientX-box.left,y=e.clientY-box.top;if(state.drag){state.start=state.drag.start-(e.clientX-state.drag.x)/(state.width-left-14)*state.span;sync();draw();return;}const rank=Math.floor((y-top)/lane);if(rank<0||rank>3||x<left||x>state.width-14)return;const time=state.start+(x-left)/(state.width-left-14)*state.span,found=hits(s.events,rank,time,state.span/(state.width-left-14)/2);hover.replaceChildren();const head=document.createElement('strong');head.textContent=`PP${rank} · ${format(time/1e6)} ms`;hover.append(head);if(!found.length){hover.append(document.createTextNode(' — no interval at this position'));return;}for(const ev of found.slice(0,5)){const line=document.createElement('div'),owner=byId.get(ev.owner_id);line.textContent=`${owner?.label||'Unattributed'} · ${ev.kind||'kernel'} · ${format(ev.duration_ns/1e3)} µs · start ${format(ev.start_ns/1e6)} ms · ${ev.id}`;hover.append(line);}if(found.length>5){const extra=document.createElement('div');extra.textContent=`${found.length-5} more overlapping intervals; zoom in to inspect.`;hover.append(extra);}});
    canvas.addEventListener('wheel',e=>{if(!e.shiftKey)return;e.preventDefault();state.start+=(e.deltaX||e.deltaY)*state.span/(state.width-left-14);sync();draw();},{passive:false});
    const observer=new ResizeObserver(()=>draw());observer.observe(canvas.parentElement);draw();
  }
  return {windowFor,xFor,hits,category,scene,mount};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=HY4Timeline;
