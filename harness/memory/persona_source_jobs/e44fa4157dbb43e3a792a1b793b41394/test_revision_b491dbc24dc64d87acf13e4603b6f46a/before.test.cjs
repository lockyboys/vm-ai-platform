// Verification of HTML embedded engine consistency, boundaries, invalid inputs, and state transitions
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { Tetris, SHAPES } = require('../engine.js');

const htmlPath = path.resolve(__dirname, '../tetris.html');
const enginePath = path.resolve(__dirname, '../engine.js');

test('tetris.html embedded engine code matches engine.js logic', () => {
  const htmlContent = fs.readFileSync(htmlPath, 'utf8');
  const engineContent = fs.readFileSync(enginePath, 'utf8').trim();

  // Extract the first script block containing the embedded engine
  const scriptMatch = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(scriptMatch, 'tetris.html must contain an embedded engine script tag');
  
  const embeddedCode = scriptMatch[1];
  // Verify IIFE contains TetrisCore definition and export to globalThis
  assert.ok(embeddedCode.includes('globalThis.TetrisCore'), 'Embedded engine must export TetrisCore to globalThis');
  
  // Execute embedded engine in a fresh VM context to ensure full behavioral consistency
  const context = { globalThis: {} };
  vm.createContext(context);
  vm.runInContext(embeddedCode, context);

  const HtmlTetris = context.globalThis.TetrisCore?.Tetris;
  const HtmlSHAPES = context.globalThis.TetrisCore?.SHAPES;

  assert.ok(HtmlTetris, 'Tetris constructor must exist in globalThis.TetrisCore');
  assert.deepEqual(HtmlSHAPES, SHAPES, 'SHAPES definitions in HTML embedded engine must match engine.js');

  // Verify functional equivalence of the two engines
  const seededRandom = () => 0.42;
  const engineGame = new Tetris({ random: seededRandom });
  const htmlGame = new HtmlTetris({ random: seededRandom });

  assert.deepEqual(htmlGame.board, engineGame.board, 'Initial board must match');
  assert.equal(htmlGame.score, engineGame.score, 'Initial score must match');
  assert.equal(htmlGame.lines, engineGame.lines, 'Initial lines must match');
  assert.equal(htmlGame.level, engineGame.level, 'Initial level must match');
  assert.equal(htmlGame.nextType, engineGame.nextType, 'Initial nextType must match');
  assert.deepEqual(htmlGame.active, engineGame.active, 'Initial active piece must match');
});

test('invalid input handling on move: null, undefined, boolean, object, symbol', () => {
  const g = new Tetris({ random: () => 0.5 });
  const initialActive = JSON.parse(JSON.stringify(g.active));

  const invalidInputs = [
    [null, 0],
    [0, null],
    [undefined, 0],
    [0, undefined],
    [true, 0],
    [0, false],
    [{}, 0],
    [[], 0],
    [() => {}, 0],
    [Symbol('invalid'), 0]
  ];

  for (const [dx, dy] of invalidInputs) {
    let result;
    try {
      result = g.move(dx, dy);
    } catch {
      result = false;
    }
    assert.equal(result, false, `move(${String(dx)}, ${String(dy)}) should return false`);
    assert.deepEqual(g.active, initialActive, `active state must not be corrupted after move(${String(dx)}, ${String(dy)})`);
  }
});

test('boundary conditions: horizontal walls and floor limits', () => {
  const g = new Tetris({ random: () => 0.5 });
  
  // Move all the way to the left wall
  for (let i = 0; i < 20; i++) {
    g.move(-1, 0);
  }
  const minX = g.active.x;
  assert.equal(g.move(-1, 0), false, 'Cannot move past left wall');
  assert.equal(g.active.x, minX, 'X coordinate must stay at boundary');

  // Move all the way to the right wall
  for (let i = 0; i < 20; i++) {
    g.move(1, 0);
  }
  const maxX = g.active.x;
  assert.equal(g.move(1, 0), false, 'Cannot move past right wall');
  assert.equal(g.active.x, maxX, 'X coordinate must stay at boundary');

  // Move down to floor
  for (let i = 0; i < 30; i++) {
    g.move(0, 1);
  }
  const maxY = g.active.y;
  assert.equal(g.move(0, 1), false, 'Cannot move past floor');
  assert.equal(g.active.y, maxY, 'Y coordinate must stay at boundary');
});

test('state transitions: pause cannot be toggled when game is over', () => {
  const g = new Tetris({ random: () => 0.5 });
  g.gameOver = true;
  g.paused = false;

  g.togglePause();
  assert.equal(g.paused, false, 'togglePause should be inert when gameOver is true');

  g.paused = true;
  g.togglePause();
  assert.equal(g.paused, true, 'togglePause should remain unchanged when gameOver is true');
});

test('state transitions: reset clears paused and gameOver states', () => {
  const g = new Tetris({ random: () => 0.5 });
  g.paused = true;
  g.gameOver = true;
  g.score = 5000;
  g.lines = 25;
  g.level = 3;

  g.reset();
  assert.equal(g.paused, false, 'reset must clear paused state');
  assert.equal(g.gameOver, false, 'reset must clear gameOver state');
  assert.equal(g.score, 0, 'reset must clear score');
  assert.equal(g.lines, 0, 'reset must clear lines');
  assert.equal(g.level, 1, 'reset must set level to 1');
  assert.ok(g.active, 'reset must spawn a new active piece');
});

test('state transitions: softDrop and hardDrop behavior when paused or game over', () => {
  const g = new Tetris({ random: () => 0.5 });
  g.paused = true;

  assert.equal(g.softDrop(), false, 'softDrop should return false when paused');
  assert.equal(g.hardDrop(), 0, 'hardDrop should return 0 when paused');

  g.paused = false;
  g.gameOver = true;
  assert.equal(g.softDrop(), false, 'softDrop should return false when game over');
  assert.equal(g.hardDrop(), 0, 'hardDrop should return 0 when game over');
});

test('HTML UI element consistency: all required interactive and display elements are present', () => {
  const html = fs.readFileSync(htmlPath, 'utf8');

  const requiredIds = [
    'board',
    'overlay',
    'eyebrow',
    'overlay-title',
    'overlay-description',
    'start',
    'score',
    'level',
    'lines',
    'status',
    'next',
    'pause',
    'restart'
  ];

  for (const id of requiredIds) {
    const idPattern = new RegExp(`id=["']${id}["']`);
    assert.ok(idPattern.test(html), `Required element with id="${id}" missing from tetris.html`);
  }

  const requiredTouchActions = ['left', 'rotate', 'right', 'down', 'drop'];
  for (const action of requiredTouchActions) {
    const actionPattern = new RegExp(`data-action=["']${action}["']`);
    assert.ok(actionPattern.test(html), `Required touch action button data-action="${action}" missing from tetris.html`);
  }
});
