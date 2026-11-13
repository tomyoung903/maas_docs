// Synthetic math tests only; never write fabricated intervals to the report.
const assert=require('node:assert/strict');
const T=require('./timeline.js');
const a={id:'a',rank:0,start_ns:10,duration_ns:20,owner_id:'x',kind:'kernel'};
const b={id:'b',rank:0,start_ns:15,duration_ns:5,owner_id:'y',kind:'kernel'};
const c={id:'c',rank:1,start_ns:100,duration_ns:10,owner_id:'z',kind:'kernel',category:'communication'};
assert.deepEqual(T.windowFor([0,100],2,0),[0,50]);
assert.deepEqual(T.windowFor([0,100],2,1),[50,100]);
assert.deepEqual(T.windowFor([0,100],1,.9),[0,100]);
assert.deepEqual(T.hits([a,b,c],0,17).map(x=>x.id),['b','a']);
assert.equal(T.hits([a,b,c],1,17).length,0);
assert.equal(T.category(c),'communication');
assert.equal(T.category({...a,kind:'memcpy'}),'memory');
assert.equal(T.category({...a,owner_id:null}),'unclassified');
assert.equal(T.scene({derived:{timeline:{available:false,reason:'no clock'}}}).available,false);
const scene=T.scene({derived:{timeline:{available:true,start_ns:0,end_ns:110}},timeline:{chunks:[]},events:[a,b,c]});
assert.equal(scene.events[2].start_ns,100); // cross-rank offset is not reset
assert.equal(scene.domain[1],110);
assert.ok(T.xFor(100,[0,110],1100)>T.xFor(10,[0,110],1100));
console.log('PASS: 12 timeline math, category, overlap and common-offset assertions');
