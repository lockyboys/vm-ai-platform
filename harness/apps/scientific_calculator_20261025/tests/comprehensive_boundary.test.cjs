// Comprehensive edge case, boundary, failure, and UI engine parity test suite
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { evaluate, CalculatorError } = require('../engine.js');

function close(actual, expected, label) {
  assert.ok(Number.isFinite(actual), `${label}: actual is not finite (${actual})`);
  assert.ok(Math.abs(actual - expected) <= 1e-10 * Math.max(1, Math.abs(expected)), `${label}: ${actual} != ${expected}`);
}

// 1. Normal and boundary calculations
test('calculate 0^0 equals 1', () => {
  // Verifying 0^0 follows JavaScript Math.pow(0, 0) == 1
  close(evaluate('0^0'), 1, '0^0');
});

test('calculate 0^5 and 0^1 equals 0', () => {
  // Verifying non-zero positive powers of zero equal 0
  close(evaluate('0^5'), 0, '0^5');
  close(evaluate('0^1'), 0, '0^1');
});

test('calculate log with custom base', () => {
  // Verifying log(value, base) semantics
  close(evaluate('log(100, 10)'), 2, 'log(100, 10)');
  close(evaluate('log(1, 10)'), 0, 'log(1, 10)');
  close(evaluate('log(27, 3)'), 3, 'log(27, 3)');
});

test('calculate trig functions at special angles', () => {
  // Verifying sin, cos, tan at 0, 180, 360 degrees
  close(evaluate('sin(0)'), 0, 'sin(0)');
  close(evaluate('cos(0)'), 1, 'cos(0)');
  close(evaluate('tan(0)'), 0, 'tan(0)');
  close(evaluate('sin(180)'), 0, 'sin(180)');
  close(evaluate('cos(180)'), -1, 'cos(180)');
  close(evaluate('tan(180)'), 0, 'tan(180)');
  close(evaluate('cos(90)'), 0, 'cos(90)');
});

test('calculate unary and binary operator chaining', () => {
  // Verifying unary minus with multiplication and division
  close(evaluate('3 * -2'), -6, '3 * -2');
  close(evaluate('-6 / -2'), 3, '-6 / -2');
  close(evaluate('2^-3'), 0.125, '2^-3');
});

test('calculate case insensitivity for functions and constants', () => {
  // Verifying case insensitivity across functions and constants
  close(evaluate('LoG10(100)'), 2, 'LoG10(100)');
  close(evaluate('EXP(0)'), 1, 'EXP(0)');
  close(evaluate('PI'), Math.PI, 'PI');
  close(evaluate('E'), Math.E, 'E');
});

// 2. Failure and rejection paths
test('reject 0 raised to negative power', () => {
  // 0^-1 leads to Infinity, which must be rejected as non-finite
  assert.throws(() => evaluate('0^-1'), CalculatorError);
});

test('reject division of zero by zero', () => {
  // 0/0 is undefined / non-finite and division by zero must throw
  assert.throws(() => evaluate('0/0'), CalculatorError);
});

test('reject tan at negative and periodic odd multiples of 90 degrees', () => {
  // tan is undefined at -90, 450, -270 degrees
  assert.throws(() => evaluate('tan(-90)'), CalculatorError);
  assert.throws(() => evaluate('tan(450)'), CalculatorError);
  assert.throws(() => evaluate('tan(-270)'), CalculatorError);
  assert.throws(() => evaluate('tan(pi/2)', 'rad'), CalculatorError);
});

test('reject invalid function arguments and arities', () => {
  // Verifying wrong argument count or invalid arguments
  assert.throws(() => evaluate('log(1, 2, 3)'), CalculatorError);
  assert.throws(() => evaluate('log(10, 0)'), CalculatorError);
  assert.throws(() => evaluate('log(0, 10)'), CalculatorError);
  assert.throws(() => evaluate('asin(1.0001)'), CalculatorError);
  assert.throws(() => evaluate('acos(-1.0001)'), CalculatorError);
});

test('reject malformed syntax and mismatched parentheses', () => {
  // Syntax errors such as operator collisions and unmatched parens
  assert.throws(() => evaluate('1+*2'), CalculatorError);
  assert.throws(() => evaluate('(1+2))'), CalculatorError);
  assert.throws(() => evaluate('((1+2)'), CalculatorError);
  assert.throws(() => evaluate('1/'), CalculatorError);
  assert.throws(() => evaluate(','), CalculatorError);
});

// 3. Boundary limits
test('enforce max tokens limit (256)', () => {
  // 127 additions: 1 + 1 + ... + 1 (128 numbers + 127 operators = 255 tokens) should pass
  const validExpr = Array(128).fill('1').join('+');
  close(evaluate(validExpr), 128, '255 tokens');

  // 128 additions: 129 numbers + 128 operators = 257 tokens should throw '수식이 너무 복잡합니다.'
  const tooComplexExpr = Array(129).fill('1').join('+');
  assert.throws(() => evaluate(tooComplexExpr), /너무 복잡합니다/);
});

test('enforce expression string length bound (> 500)', () => {
  // Length > 500 must throw '1~500자의 수식을 입력하세요.'
  const longExpr = '1'.repeat(501);
  assert.throws(() => evaluate(longExpr), /1~500자의 수식을 입력하세요/);
});

// 4. Engine and HTML UI parity verification
test('verify HTML embedded engine matches engine.js implementation', () => {
  const htmlPath = path.join(__dirname, '..', 'scientific_calculator.html');
  const htmlContent = fs.readFileSync(htmlPath, 'utf8');

  // Extract the engine code embedded in the first script tag of scientific_calculator.html
  const match = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(match, 'HTML must contain first script tag with engine definition');
  const embeddedCode = match[1];

  const sandbox = { globalThis: {} };
  vm.createContext(sandbox);
  vm.runInContext(embeddedCode, sandbox);

  const htmlCore = sandbox.globalThis.CalculatorCore;
  assert.ok(htmlCore && typeof htmlCore.evaluate === 'function', 'Embedded engine must export evaluate');

  // Compare evaluations between standalone engine and embedded engine
  const testExpressions = [
    ['2+3*4', 'deg'],
    ['sin(30)+sqrt(16)', 'deg'],
    ['tan(pi/4)', 'rad'],
    ['log(100, 10)', 'deg'],
    ['(-2)^2', 'deg'],
    ['2^-2', 'deg'],
    ['170!', 'deg'],
    ['0^0', 'deg']
  ];

  for (const [expr, mode] of testExpressions) {
    const engineRes = evaluate(expr, mode);
    const htmlRes = htmlCore.evaluate(expr, mode);
    assert.strictEqual(engineRes, htmlRes, `Engine parity mismatch for "${expr}" (${mode})`);
  }

  // Compare error handling parity
  const errorExpressions = ['1/0', 'tan(90)', 'sqrt(-1)', 'log(10, 1)'];
  for (const expr of errorExpressions) {
    assert.throws(() => evaluate(expr, 'deg'), /.*/, `engine.js must throw for ${expr}`);
    assert.throws(() => htmlCore.evaluate(expr, 'deg'), /.*/, `HTML engine must throw for ${expr}`);
  }
});
