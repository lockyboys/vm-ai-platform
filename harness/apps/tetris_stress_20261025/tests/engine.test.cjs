// Independent gameplay acceptance tests: no browser, network, or mocked engine.
const test = require('node:test');
const assert = require('node:assert/strict');
const {Tetris, SHAPES} = require('../engine.js');
const copy = x => JSON.parse(JSON.stringify(x));
function game() { return new Tetris({random: () => 0.5}); }
function piece(g, type, x, y, shape = SHAPES[type]) {
  g.active = {type, x, y, shape: copy(shape)};
}
function single(g) {
  g.board[19].fill('J'); g.board[19][4] = g.board[19][5] = 0;
  piece(g, 'O', 4, 18); g.lock();
}
test('initial board, state and independent rows', () => {
  const g=game(); assert.equal(g.board.length,20);
  assert.ok(g.board.every(r=>r.length===10 && r.every(c=>c===0)));
  assert.equal(g.score,0); assert.equal(g.lines,0); assert.equal(g.level,1);
  assert.ok(g.active); assert.equal(g.gameOver,false);
  g.board[0][0]='T'; assert.equal(g.board[1][0],0);
});
test('all seven tetrominoes contain exactly four cells', () => {
  assert.deepEqual(Object.keys(SHAPES).sort(),['I','J','L','O','S','T','Z']);
  for(const s of Object.values(SHAPES)) assert.equal(s.flat().filter(Boolean).length,4);
});
test('each seven-bag includes every type once', () => {
  const g=game(), types=[];
  for(let i=0;i<14;i++){ types.push(g.active.type); g.spawn(); }
  assert.equal(new Set(types.slice(0,7)).size,7);
  assert.equal(new Set(types.slice(7)).size,7);
});
test('movement changes coordinates without modifying board', () => {
  const g=game(); piece(g,'O',4,0); const board=copy(g.board);
  assert.equal(g.move(-1),true); assert.equal(g.active.x,3);
  assert.equal(g.move(0,1),true); assert.equal(g.active.y,1);
  assert.deepEqual(g.board,board);
});
test('left wall, right wall, floor and occupied cells reject collisions', () => {
  const g=game(); piece(g,'O',0,18);
  assert.equal(g.move(-1),false); assert.equal(g.move(0,1),false);
  piece(g,'O',8,0); assert.equal(g.move(1),false);
  g.board[2][8]='T'; assert.equal(g.move(0,1),false);
});
test('above-board cells are allowed until locking', () => {
  const g=game(); assert.equal(g.collides(SHAPES.O,4,-1),false);
});
test('clockwise rotation preserves cell count and global shapes', () => {
  const g=game(), originals=copy(SHAPES); piece(g,'T',3,3);
  const before=copy(g.active.shape); assert.equal(g.rotate(),true);
  assert.notDeepEqual(g.active.shape,before);
  assert.equal(g.active.shape.flat().filter(Boolean).length,4);
  assert.deepEqual(SHAPES,originals);
  for(let i=0;i<3;i++) g.rotate(); assert.deepEqual(g.active.shape,before);
});
test('rotation uses a horizontal wall kick', () => {
  const g=game(); piece(g,'T',8,3,[[1,0],[1,1],[1,0]]);
  assert.equal(g.rotate(),true); assert.equal(g.active.x,7);
  assert.equal(g.collides(g.active.shape,g.active.x,g.active.y),false);
});
test('blocked rotation preserves coordinates and shape', () => {
  const g=game(); g.board.forEach(r=>r.fill('J')); piece(g,'T',3,3);
  const before=copy(g.active); assert.equal(g.rotate(),false);
  assert.deepEqual(g.active,before);
});
test('tick locks a landed piece and spawns the queued next type', () => {
  const g=game(); piece(g,'O',4,18); const next=g.nextType; g.tick();
  assert.equal(g.active.type,next); assert.equal(g.board.flat().filter(Boolean).length,4);
  assert.equal(g.board[19][4],'O');
});
test('soft drop scores one point for a successful step only', () => {
  const g=game(); piece(g,'O',4,17);
  assert.equal(g.softDrop(),true); assert.equal(g.score,1);
  assert.equal(g.softDrop(),false); assert.equal(g.score,1);
});
test('hard drop lands, scores distance and locks exactly four cells', () => {
  const g=game(); piece(g,'O',4,0);
  assert.equal(g.hardDrop(),18); assert.equal(g.score,36);
  assert.equal(g.board.flat().filter(Boolean).length,4);
});
test('ghost is the landing position and does not mutate live state', () => {
  const g=game(); piece(g,'O',4,2); const before=copy({a:g.active,b:g.board});
  const ghost=g.ghost(); assert.equal(ghost.y,18);
  assert.deepEqual({a:g.active,b:g.board},{a:before.a,b:before.b});
  ghost.shape[0][0]=0; assert.equal(g.active.shape[0][0],1);
});
test('single line clears, shifts rows, and awards 100', () => {
  const g=game(); single(g);
  assert.equal(g.lines,1); assert.equal(g.score,100);
  assert.equal(g.board[19][4],'O'); assert.equal(g.board[19][5],'O');
  assert.equal(g.board.flat().filter(Boolean).length,2);
});
test('four simultaneous lines award 800 and leave no remnants', () => {
  const g=game(); for(let y=16;y<20;y++){g.board[y].fill('J');g.board[y][4]=0;}
  piece(g,'I',4,16,[[1],[1],[1],[1]]); g.lock();
  assert.equal(g.lines,4); assert.equal(g.score,800);
  assert.equal(g.board.flat().filter(Boolean).length,0);
});
test('nonadjacent complete rows clear simultaneously', () => {
  const g=game(); g.board[17].fill('J'); g.board[19].fill('J');
  piece(g,'O',0,0); g.lock();
  assert.equal(g.lines,2); assert.equal(g.score,300);
  assert.equal(g.board.flat().filter(Boolean).length,4);
});
test('level increases every ten lines and scoring uses the prior level', () => {
  const g=game(); g.lines=9; single(g);
  assert.equal(g.level,2); assert.equal(g.score,100);
  g.board=Array.from({length:20},()=>Array(10).fill(0)); single(g);
  assert.equal(g.score,300);
});
test('spawn collision ends the game', () => {
  const g=game(); g.board[0].fill('J'); g.spawn(); assert.equal(g.gameOver,true);
});
test('top-out locking does not partially write the board', () => {
  const g=game(); piece(g,'O',4,-1); const before=copy(g.board); g.lock();
  assert.equal(g.gameOver,true); assert.deepEqual(g.board,before);
});
test('pause blocks movement, rotation, gravity, scoring and locking', () => {
  const g=game(); g.togglePause(); const before=copy({a:g.active,b:g.board,s:g.score});
  assert.equal(g.move(1),false); assert.equal(g.rotate(),false);
  assert.equal(g.softDrop(),false); assert.equal(g.hardDrop(),0); g.tick();g.lock();
  assert.deepEqual({a:g.active,b:g.board,s:g.score},before);
  g.togglePause(); assert.equal(g.paused,false);
});
test('game-over input is inert, and reset creates a playable new game', () => {
  const g=game();g.gameOver=true;const before=copy(g.active);
  assert.equal(g.move(1),false);assert.equal(g.rotate(),false);
  assert.equal(g.hardDrop(),0);g.tick();g.togglePause();assert.deepEqual(g.active,before);
  g.score=900;g.reset();assert.equal(g.score,0);assert.equal(g.gameOver,false);
});
test('long deterministic play preserves board dimensions and terminates safely', () => {
  const g=game(); for(let i=0;i<200;i++){g.rotate();g.move(i%2?1:-1);g.hardDrop();}
  assert.equal(g.board.length,20); assert.ok(g.board.every(r=>r.length===10));
  assert.equal(g.gameOver,true);
});
