// Deterministic stress tests report reproducible seeds and check game invariants.
const test=require('node:test'),assert=require('node:assert/strict');
const {Tetris,SHAPES}=require('../engine.js');
function seeded(seed){let state=seed>>>0;return()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};}
function invariants(g,context){
 assert.equal(g.board.length,20,context);assert.ok(g.board.every(r=>r.length===10),context);
 assert.equal(new Set(g.board).size,20,context);
 for(const row of g.board)for(const value of row)assert.ok(value===0||Object.hasOwn(SHAPES,value),context);
 assert.ok(Number.isFinite(g.score)&&g.score>=0,context);
 assert.equal(g.level,Math.floor(g.lines/10)+1,context);
 assert.ok(Number.isInteger(g.active.x)&&Number.isInteger(g.active.y),context);
 if(!g.gameOver){
   assert.equal(g.collides(g.active.shape,g.active.x,g.active.y),false,context);
   const ghost=g.ghost();assert.ok(ghost.y>=g.active.y,context);
   assert.equal(g.collides(ghost.shape,ghost.x,ghost.y),false,context);
   assert.equal(g.collides(ghost.shape,ghost.x,ghost.y+1),true,context);
 }
}
test('1,000,000 seeded gameplay actions preserve state invariants',()=>{
 for(let seed=1;seed<=200;seed++){
   const random=seeded(seed),g=new Tetris({random});
   for(let step=0;step<5000;step++){
     const context=`seed=${seed},step=${step}`;
     if(g.gameOver){g.reset();}
     const action=Math.floor(random()*10);
     switch(action){case 0:g.move(-1);break;case 1:g.move(1);break;case 2:g.rotate();break;
       case 3:case 4:g.tick();break;case 5:case 6:g.softDrop();break;
       case 7:g.hardDrop();break;case 8:g.togglePause();break;case 9:if(random()<.03)g.reset();break;}
     if(step%17===0)invariants(g,context);
   }
   invariants(g,`seed=${seed},final`);
 }
});
test('10,000 randomized line-clears match an independent board oracle',()=>{
 const random=seeded(0x51a7);
 for(let fixture=0;fixture<10000;fixture++){
   const g=new Tetris({random}),count=1+Math.floor(random()*4),x=Math.floor(random()*10);
   const priorLevel=1+Math.floor(random()*50);
   g.level=priorLevel;g.lines=(priorLevel-1)*10+Math.floor(random()*10);
   const oldLines=g.lines;
   for(let y=20-count;y<20;y++){g.board[y].fill('J');g.board[y][x]=0;}
   g.active={type:'I',shape:[[1],[1],[1],[1]],x,y:16};
   const expected=g.board.map(r=>r.slice());for(let y=16;y<20;y++)expected[y][x]='I';
   const survivors=expected.filter(r=>!r.every(Boolean));
   const oracle=[...Array.from({length:20-survivors.length},()=>Array(10).fill(0)),...survivors];
   g.lock();assert.deepEqual(g.board,oracle,`fixture=${fixture}`);
   assert.equal(g.score,[0,100,300,500,800][count]*priorLevel);
   assert.equal(g.lines,oldLines+count);invariants(g,`fixture=${fixture}`);
 }
});
test('10,000 seven-bags contain every tetromino exactly once',()=>{
 const g=new Tetris({random:seeded(98765)});g.bag=[];
 for(let bag=0;bag<10000;bag++){
   const types=Array.from({length:7},()=>g.draw());
   assert.equal(new Set(types).size,7,`bag=${bag}`);
 }
});
