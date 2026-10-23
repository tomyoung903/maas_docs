/** Animated, self-contained diagrams for the Kimi K3 KDA walkthrough.
 * All state matrices and vectors are schematic crops, never numerical traces.
 */

const C = { ink: 'var(--ink, #eef5fc)', muted: 'var(--muted, #a9bfd2)', line: 'var(--line, #334b64)', cyan: 'var(--cyan, #59d9e3)', gold: 'var(--gold, #ffc16a)', purple: 'var(--purple, #b69cff)', green: 'var(--green, #68e2b5)' };
const esc = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const label = (x,y,s,fill=C.ink,size=23,anchor='middle',cls='') => `<text x="${x}" y="${y}" text-anchor="${anchor}" fill="${fill}" font-size="${size}" class="${cls}">${esc(s)}</text>`;
const rect = (x,y,w,h,fill='rgba(20,39,58,.86)',stroke=C.line,r=17,extra='') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="2" ${extra}/>`;
const card = (x,y,w,h,title,subtitle='',color=C.cyan) => `<g>${rect(x,y,w,h,undefined,color)}${label(x+w/2,y+(subtitle?h/2-4:h/2+8),title,C.ink,25)}${subtitle?label(x+w/2,y+h/2+29,subtitle,C.muted,19):''}</g>`;
const route = (id,d,color=C.muted,dashed=false) => `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.5" ${dashed?'stroke-dasharray="7 7"':''} marker-end="url(#arrow-${id})"/>`;
const packet = (x,y,dx,dy,color=C.cyan,delay=0) => `<g transform="translate(${x} ${y})"><circle r="6" fill="${color}" class="kda-packet" style="--dx:${dx}px;--dy:${dy}px;animation-delay:${delay}s"/></g>`;
const footer = s => label(500,472,s,C.muted,19);
function matrix(x,y,size=240,{color=C.cyan,cls='',rows=8,values=false,alpha=1}={}) {
  const gap=3, cell=(size-gap*(rows-1))/rows;
  let out=`<g class="${cls}">${rect(x-8,y-8,size+16,size+16,'rgba(20,39,58,.45)',C.line,12)}`;
  for(let r=0;r<rows;r++) for(let c=0;c<rows;c++) {
    const a=alpha*(.18+((r*11+c*7+3)%13)/18);
    out+=`<rect x="${x+c*(cell+gap)}" y="${y+r*(cell+gap)}" width="${cell}" height="${cell}" rx="3" fill="${color}" opacity="${a.toFixed(3)}" class="${values?'kda-memory-cell':''}" style="--row:${r};--col:${c};--base-opacity:${a.toFixed(3)};animation-delay:${((r+c)*.08).toFixed(2)}s"/>`;
  }
  return out+'</g>';
}
function vector(x,y,{h=232,w=30,color=C.gold,cls='',cells=8,vertical=true}={}) {
  const gap=3, dh=(h-(cells-1)*gap)/cells;
  let s=`<g class="${cls}">`;
  for(let i=0;i<cells;i++) s+=`<rect x="${x+(vertical?0:i*(dh+gap))}" y="${y+(vertical?i*(dh+gap):0)}" width="${vertical?w:dh}" height="${vertical?dh:w}" rx="3" fill="${color}" opacity="${(.35+(i*5%7)*.09).toFixed(2)}"/>`;
  return s+'</g>';
}

const views = {
  overview(id) {
    return label(500,58,'One KDA module · the complete path',C.ink,29)+
      card(24,193,126,100,'Input X','7,168',C.ink)+
      card(196,193,156,100,'Project','Q · K · V',C.cyan)+
      card(398,193,154,100,'Local mix','causal width 4',C.cyan)+
      card(598,193,170,100,'KDA memory','96 heads',C.purple)+
      card(814,193,162,100,'Output','7,168',C.green)+
      route(id,'M150 243 H188')+route(id,'M352 243 H390')+route(id,'M552 243 H590')+route(id,'M768 243 H806')+
      packet(154,243,34,0,C.cyan)+packet(356,243,34,0,C.cyan,.8)+packet(556,243,34,0,C.purple,1.6)+packet(772,243,34,0,C.green,2.4)+
      card(598,66,170,66,'Sₜ₋₁ → Sₜ','',C.purple)+route(id,'M683 132 V185',C.purple)+
      label(275,344,'12,288 = 96 × 128',C.cyan,22)+label(686,344,'Fixed-size state',C.purple,22)+
      footer('Example: one sequence · 100,000 input tokens · tensor shapes stay explicit on each slide');
  },
  projections(id) {
    let s=label(500,49,'Three independent projections',C.ink,29)+card(34,203,185,104,'Input X','7,168 channels',C.ink);
    for(const [i,name,color] of [[0,'Q',C.cyan],[1,'K',C.gold],[2,'V',C.purple]]) {
      const y=72+i*132;
      s+=route(id,`M219 255 H285 V${y+43} H345`,color)+card(355,y,250,86,`${name} projection`,'7,168 → 12,288',color)+
        route(id,`M605 ${y+43} H675`,color)+card(687,y,276,86,`${name}₀`,'1 × 100,000 × 12,288',color)+packet(612,y+43,61,0,color,-i*1.4);
    }
    return s+footer('Q, K and V have separate learned weights. No low-rank bottleneck in these three paths.');
  },
  'local-mixing'(id) {
    let s=label(500,48,'Each token mixes only with its recent past',C.ink,29);
    const xs=[120,230,340,450,560,670,780];
    xs.forEach((x,i)=>s+=card(x,124,87,71,i<4?`t − ${4-i}`:i===4?'t':`t + ${i-4}`,'',i>4?C.line:C.cyan));
    s+=`<rect x="218" y="110" width="441" height="100" rx="22" fill="none" stroke="${C.gold}" stroke-width="3" class="kda-window"/>`;
    s+=label(444,92,'Width-4 causal window',C.gold,23);
    for(let i=1;i<=4;i++)s+=route(id,`M${xs[i]+43} 198 V244 L500 287`,C.cyan);
    s+=card(361,293,278,95,'Depthwise conv + SiLU','separate Q / K / V streams',C.cyan)+
      label(820,245,'Future tokens',C.muted,20)+label(820,272,'are excluded',C.muted,20)+
      footer('After mixing: split into 96 heads. L2-normalize Q and K; keep V unnormalized.');
    return s;
  },
  gates(id) {
    let s=label(500,44,'Three controls derived from the same input',C.ink,28)+card(25,191,160,94,'Input X','7,168 channels',C.ink);
    s+=route(id,'M185 237 H229 V114 H265',C.gold)+card(275,71,207,85,'Down-project','7,168 → 128',C.gold)+route(id,'M482 114 H530',C.gold)+card(542,71,201,85,'Up-project','128 → 12,288',C.gold)+route(id,'M743 114 H789',C.gold)+card(801,71,173,85,'Retention α','96 × 128',C.gold);
    s+=route(id,'M185 237 H270',C.purple)+card(282,194,274,86,'Write strength β','7,168 → 96',C.purple)+route(id,'M556 237 H788',C.purple)+card(800,194,174,86,'One scalar','per head',C.purple);
    s+=route(id,'M185 237 H229 V360 H271',C.green)+card(282,318,274,86,'Output gate','7,168 → 12,288',C.green)+route(id,'M556 361 H788',C.green)+card(800,318,174,86,'96 × 128','sigmoid gate',C.green);
    s+=packet(490,114,40,0,C.gold)+packet(565,237,220,0,C.purple,-1.6)+packet(565,361,220,0,C.green,-3.2);
    return s+footer('The retention path is low-rank; β and the output gate are distinct learned projections.');
  },
  state(id) {
    return label(500,48,'S is a running key-to-value memory',C.ink,29)+
      `<g opacity=".23">${matrix(380,92,260,{color:C.purple})}</g><g opacity=".38">${matrix(370,102,260,{color:C.purple})}</g>`+
      matrix(360,112,260,{color:C.purple,values:true})+
      label(491,97,'128 value dimensions →',C.purple,22)+`<text transform="translate(322 248) rotate(-90)" text-anchor="middle" fill="${C.purple}" font-size="22">128 key dimensions →</text>`+
      card(36,184,216,108,'Sₜ₋₁','before token t',C.purple)+route(id,'M252 238 H338',C.purple)+
      card(726,184,234,108,'Sₜ','after token t',C.green)+route(id,'M642 238 H714',C.green)+
      label(499,405,'One matrix per head · 96 heads',C.ink,23)+
      footer('Small grid is schematic. State shape: [1, 96, 128 key, 128 value]; it does not grow with T.');
  },
  retain(id) {
    let s=label(500,46,'1 · Retain selected parts of the old memory',C.ink,28)+label(214,112,'Sₜ₋₁',C.purple,30)+matrix(94,142,240,{color:C.purple});
    s+=label(449,112,'αₜ',C.gold,30)+vector(433,145,{color:C.gold})+label(449,416,'128 values',C.gold,20);
    s+=label(785,112,'S̄ₜ',C.cyan,30)+matrix(665,142,240,{color:C.cyan,cls:'kda-retained'});
    s+=route(id,'M348 262 H403',C.muted)+label(510,271,'× each row',C.ink,23)+route(id,'M572 262 H645',C.cyan)+
      packet(578,262,60,0,C.cyan);
    return s+footer('Each α value scales one key row across all value columns. The grid is a schematic crop.');
  },
  predict(id) {
    let s=label(500,46,'2 · Predict the value already stored at this key',C.ink,28);
    s+=label(215,105,'Retained memory S̄ₜᵀ',C.cyan,24)+matrix(95,133,240,{color:C.cyan})+label(366,264,'×',C.ink,33)+vector(397,137,{color:C.gold})+label(411,108,'k̂ₜ',C.gold,26)+
      route(id,'M451 253 H516',C.muted)+label(555,108,'Predicted v',C.cyan,24)+vector(540,137,{color:C.cyan})+
      label(727,108,'Actual vₜ',C.purple,24)+vector(711,137,{color:C.purple})+
      route(id,'M575 253 H622 V377 H785',C.cyan)+label(671,363,'subtract',C.cyan,21)+
      route(id,'M757 253 H865 V321',C.purple)+label(842,281,'from',C.purple,21)+
      `<g class="kda-pulse">${card(796,330,178,91,'Residual eₜ','128 values',C.green)}</g>`;
    return s+footer('eₜ = actual value − predicted value. The residual is what this token still needs to write.');
  },
  write(id) {
    let s=label(500,45,'3 · Write a key × residual correction',C.ink,29);
    s+=label(116,111,'Key k̂ₜ',C.gold,24)+vector(98,146,{color:C.gold})+
      label(184,265,'×',C.ink,32)+label(287,111,'Residual eₜᵀ',C.green,24)+vector(203,226,{h:169,w:31,color:C.green,vertical:false})+
      route(id,'M388 244 H437',C.muted)+label(576,111,'βₜ k̂ₜ eₜᵀ',C.green,26)+matrix(465,144,222,{color:C.green,cls:'kda-outer-product'})+
      label(736,264,'+',C.ink,32)+card(780,183,179,115,'Old S̄ₜ','retained memory',C.cyan)+
      route(id,'M892 303 V370 H607',C.purple)+card(365,392,356,48,'Sₜ = S̄ₜ + correction','',C.purple);
    return s+footer('The small grid is schematic. β is one scalar per head; the correction is a 128 × 128 matrix.');
  },
  read(id) {
    let s=label(500,47,'4 · Read from the updated memory',C.ink,29)+label(219,109,'Updated Sₜᵀ',C.purple,25)+matrix(99,143,240,{color:C.purple,values:true});
    s+=label(400,265,'×',C.ink,34)+label(506,110,'q̂ₜ / √128',C.gold,26)+vector(489,145,{color:C.gold})+
      route(id,'M570 260 H666',C.muted)+packet(577,260,78,0,C.green)+label(767,110,'Output oₜ',C.green,26)+vector(750,145,{color:C.green,cls:'kda-pulse'})+
      label(219,415,'128 value × 128 key',C.purple,21)+label(767,415,'128 value dimensions',C.green,21);
    return s+footer('Read uses Sₜ, including the current token’s update. Formula: oₜ = Sₜᵀ(q̂ₜ / √128).');
  },
  output(id) {
    let s=label(500,45,'Normalize, gate, and return to model width',C.ink,29);
    const cards=[[25,150,'Head output','96 × 128',C.purple],[270,150,'RMSNorm','per 128-channel head',C.cyan],[515,150,'× sigmoid(g)','output gate',C.gold],[760,150,'Concatenate','12,288',C.green]];
    for(const [x,y,t,sub,c] of cards)s+=card(x,y,210,104,t,sub,c);
    for(const x of [235,480,725])s+=route(id,`M${x} 202 H${x+25}`,C.muted)+packet(x+3,202,17,0,C.green,-x/150);
    s+=route(id,'M865 255 V328 H639',C.green)+card(359,302,268,112,'Output projection','12,288 → 7,168',C.green)+
      label(502,276,'Every input token gets an output',C.muted,21);
    return s+footer('Output shape: [1, 100,000, 7,168]. The state remains separate from these token outputs.');
  },
  execution(id) {
    let s=label(500,43,'The same recurrence has two execution paths',C.ink,28)+label(251,90,'PREFILL · 100,000 tokens',C.cyan,24)+label(755,90,'DECODE · one new token',C.gold,24);
    s+=`<line x1="501" y1="110" x2="501" y2="417" stroke="${C.line}" stroke-width="2"/>`;
    for(let i=0;i<4;i++) {
      const x=34+i*114;
      s+=card(x,157,99,79,`Chunk ${i+1}`,'',C.cyan)+`<g class="kda-chunk" style="animation-delay:${i*.65}s">`;
      for(let j=0;j<4;j++)s+=`<rect x="${x+12+j*19}" y="205" width="14" height="17" rx="3" fill="${C.cyan}"/>`;
      s+='</g>';
      if(i<3)s+=route(id,`M${x+99} 196 H${x+108}`,C.purple);
    }
    s+=label(250,287,'Parallel work inside each chunk',C.cyan,21)+label(250,320,'Carry state between chunks',C.purple,21)+
      card(560,155,155,91,'Sₜ₋₁','previous state',C.purple)+route(id,'M715 200 H754',C.purple)+card(767,155,168,91,'Token t','one update',C.gold)+
      route(id,'M851 247 V300 H717',C.green)+card(560,280,145,73,'Sₜ','',C.green)+packet(719,200,30,0,C.gold)+
      label(752,393,'Use updated state next step',C.muted,20);
    return s+footer('Conceptual schedule: prefill is not 100,000 serial GPU updates, nor a 100K × 100K attention matrix.');
  },
  recap(id) {
    let s=label(500,46,'One token, one head: four memory operations',C.ink,28);
    const nodes=[['Retain','Scale old memory',C.gold],['Predict','Predict value',C.cyan],['Write','Add correction',C.green],['Read','Read with query',C.purple]];
    nodes.forEach(([t,sub,c],i)=>{
      const x=23+i*247;
      s+=card(x,190,220,117,t,sub,c);
      if(i<3)s+=route(id,`M${x+220} 248 H${x+238}`,C.muted)+packet(x+223,248,12,0,c,-i*1.15);
    });
    s+=label(500,128,'Sₜ₋₁: before token t  →  Sₜ: after token t',C.ink,24)+label(500,372,'State: 96 heads × 128 key dimensions × 128 value dimensions',C.purple,22)+
      footer('t is token position, not layer number. The state is runtime memory, not learned model weights.');
    return s;
  }
};

export function renderDiagram(slideId) {
  const view=views[slideId];
  if(!view) throw new Error(`Unknown KDA diagram: ${slideId}`);
  return `<svg class="kda-viz" viewBox="0 0 1000 500" role="img" aria-labelledby="title-${slideId} desc-${slideId}" xmlns="http://www.w3.org/2000/svg"><title id="title-${slideId}">Kimi K3 KDA: ${esc(slideId.replaceAll('-',' '))}</title><desc id="desc-${slideId}">Animated schematic of the ${esc(slideId.replaceAll('-',' '))} stage. Exact tensor dimensions and explanation are provided beside the diagram. Colored matrices and vectors show structure, not measured activations.</desc><defs><marker id="arrow-${slideId}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 Z" fill="${C.muted}"/></marker></defs>${view(slideId)}</svg>`;
}

export const animationsCSS = `
.kda-viz{display:block;width:100%;height:auto;overflow:visible;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.kda-viz text{paint-order:stroke;stroke:none;font-weight:500;letter-spacing:-.015em}
.kda-viz .kda-packet{animation:kda-travel 6s linear infinite}
.kda-viz .kda-memory-cell{animation:kda-memory 6s ease-in-out infinite}
.kda-viz .kda-pulse{animation:kda-pulse 6s ease-in-out infinite}
.kda-viz .kda-window{animation:kda-window 6s ease-in-out infinite}
.kda-viz .kda-retained rect:not(:first-child){animation:kda-retain 6s ease-in-out infinite;animation-delay:calc(var(--row,0) * .12s)}
.kda-viz .kda-outer-product rect:not(:first-child){animation:kda-write 6s ease-in-out infinite;animation-delay:calc((var(--row,0) + var(--col,0)) * .11s)}
.kda-viz .kda-chunk{animation:kda-chunk 6s ease-in-out infinite}
.deck.is-paused .kda-viz *, .deck[data-paused="true"] .kda-viz *{animation-play-state:paused!important}
@keyframes kda-travel{0%,8%{transform:translate(0,0);opacity:0}12%{opacity:1}54%,100%{transform:translate(var(--dx),var(--dy));opacity:0}}
@keyframes kda-memory{0%,100%{opacity:var(--base-opacity,.55)}38%,58%{opacity:.92}}
@keyframes kda-pulse{0%,100%{opacity:.42}35%,70%{opacity:1}}
@keyframes kda-window{0%,100%{stroke-opacity:.5;fill:rgba(255,193,106,0)}30%,65%{stroke-opacity:1;fill:rgba(255,193,106,.07)}}
@keyframes kda-retain{0%,100%{opacity:.7}35%,72%{opacity:calc(.16 + var(--row,0) * .085)}}
@keyframes kda-write{0%,12%,100%{opacity:.08}32%,74%{opacity:.85}}
@keyframes kda-chunk{0%,10%,100%{opacity:.12}24%,57%{opacity:1}}
@media(prefers-reduced-motion:reduce){.deck:not(.motion-opt-in) .kda-viz *{animation:none!important}.deck:not(.motion-opt-in) .kda-viz .kda-packet{display:none}.deck:not(.motion-opt-in) .kda-viz .kda-chunk{opacity:.8}}
`;
