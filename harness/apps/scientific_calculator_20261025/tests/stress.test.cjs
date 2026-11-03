const test=require('node:test'),assert=require('node:assert/strict');
const {evaluate}=require('../engine.js');
function rng(seed){let x=seed>>>0;return()=>{x=(Math.imul(x,1664525)+1013904223)>>>0;return x/4294967296;};}
function close(a,b,label){assert.ok(Number.isFinite(a)&&Math.abs(a-b)<=1e-9*Math.max(1,Math.abs(b)),`${label}: ${a} vs ${b}`);}
test('50,000 seeded arithmetic expressions agree with independent arithmetic',()=>{
 const r=rng(20261025);
 for(let i=0;i<50000;i++){
  const a=Math.floor(r()*2000)-1000,b=Math.floor(r()*2000)-1000,c=1+Math.floor(r()*99);
  const expr=`((${a})+(${b}))*${c}/7`;
  close(evaluate(expr),(a+b)*c/7,`seed=20261025,case=${i},${expr}`);
 }
});
test('10,000 trig, log and square-root cases agree with Math',()=>{
 const r=rng(88551);
 for(let i=0;i<10000;i++){
  const x=r()*2000-1000,y=.01+r()*100;
  close(evaluate(`sin(${x})`),Math.sin(x*Math.PI/180),'sin');
  close(evaluate(`cos(${x})`),Math.cos(x*Math.PI/180),'cos');
  close(evaluate(`ln(${y})`),Math.log(y),'ln');
  close(evaluate(`sqrt(${y})`),Math.sqrt(y),'sqrt');
 }
});
test('5,000 angle round-trips preserve degree/radian semantics',()=>{
 const r=rng(44);
 for(let i=0;i<5000;i++){
  const degrees=r()*178-89,radians=degrees*Math.PI/180;
  close(evaluate(`asin(sin(${degrees}))`,'deg'),degrees,'degree round-trip');
  close(evaluate(`atan(tan(${radians}))`,'rad'),radians,'radian round-trip');
 }
});
