// Regressions for actual failures in the delivered engine, without injecting faults.
const test=require('node:test'), assert=require('node:assert/strict');
const {Tetris,SHAPES}=require('../engine.js');
for(const [name,dx,dy] of [
 ['fractional horizontal movement',0.5,0],['fractional vertical movement',0,0.5],
 ['NaN horizontal movement',NaN,0],['NaN vertical movement',0,NaN],
 ['infinite upward movement',0,-Infinity],['string movement','1',0],
 ['billion-row upward movement',0,-1000000000],
])test(name+' is rejected without corrupting state',()=>{
 const g=new Tetris(),before=JSON.stringify(g.active);
 assert.equal(g.move(dx,dy),false);
 assert.equal(JSON.stringify(g.active),before);
});
test('exported shape matrices and rows are immutable',()=>{
 for(const shape of Object.values(SHAPES)){
   assert.equal(Object.isFrozen(shape),true);
   assert.ok(shape.every(Object.isFrozen));
 }
});
