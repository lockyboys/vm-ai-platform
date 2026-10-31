// Bounded scientific-expression parser. No eval, dynamic functions or external I/O.
(function (root) {
  'use strict';
  class CalculatorError extends Error {
    constructor(message) { super(message); this.name = 'CalculatorError'; }
  }
  function finite(value) {
    if (!Number.isFinite(value)) throw new CalculatorError('실수 범위를 벗어난 계산입니다.');
    return value;
  }
  function factorial(value) {
    if (!Number.isInteger(value) || value < 0 || value > 170)
      throw new CalculatorError('팩토리얼은 0~170 사이 정수만 가능합니다.');
    let result = 1;
    for (let n = 2; n <= value; n++) result *= n;
    return finite(result);
  }
  function evaluate(expression, angleMode = 'deg') {
    if (typeof expression !== 'string' || !expression.trim() || expression.length > 500)
      throw new CalculatorError('1~500자의 수식을 입력하세요.');
    if (angleMode !== 'deg' && angleMode !== 'rad')
      throw new CalculatorError('각도 단위는 deg 또는 rad입니다.');
    const source = expression.trim().toLowerCase()
      .replace(/π/g, 'pi').replace(/×/g, '*').replace(/÷/g, '/').replace(/−/g, '-');
    // Sticky tokenization rejects unsupported characters instead of skipping them.
    const pattern = /\s*(?:(\d+(?:\.\d*)?|\.\d+)(?:([e][+-]?\d+))?|([a-z_][a-z0-9_]*)|(\*\*|[+\-*/^!%(),]))/y;
    const tokens = [];
    let offset = 0;
    while (offset < source.length) {
      pattern.lastIndex = offset;
      const match = pattern.exec(source);
      if (!match) throw new CalculatorError('지원하지 않는 문자 또는 수식입니다.');
      offset = pattern.lastIndex;
      if (match[1] !== undefined)
        tokens.push({kind:'number', value:finite(Number(match[1] + (match[2] || '')))});
      else if (match[3] !== undefined) tokens.push({kind:'name', value:match[3]});
      else tokens.push({kind:'operator', value:match[4]});
      if (tokens.length > 256) throw new CalculatorError('수식이 너무 복잡합니다.');
    }
    let position = 0, depth = 0;
    const peek = value => tokens[position] && tokens[position].value === value;
    function take(value) {
      const token = tokens[position++];
      if (!token || (value !== undefined && token.value !== value))
        throw new CalculatorError('수식 또는 괄호를 확인하세요.');
      return token;
    }
    const toRadians = value => angleMode === 'deg' ? (value % 360) * Math.PI / 180 : value;
    const fromRadians = value => angleMode === 'deg' ? value * 180 / Math.PI : value;
    const arities = Object.freeze({sin:1,cos:1,tan:1,asin:1,acos:1,atan:1,
      sqrt:1,abs:1,ln:1,log10:1,exp:1,floor:1,ceil:1,round:1,factorial:1,log:2});
    function call(name, args) {
      if (!Object.hasOwn(arities,name) || args.length !== arities[name])
        throw new CalculatorError('함수 이름과 인자 개수를 확인하세요.');
      const x = args[0];
      switch (name) {
        case 'sin': return finite(Math.sin(toRadians(x)));
        case 'cos': return finite(Math.cos(toRadians(x)));
        case 'tan': {
          const radians = toRadians(x);
          if (Math.abs(Math.cos(radians)) < 1e-12)
            throw new CalculatorError('이 각도에서 tan은 정의되지 않습니다.');
          return finite(Math.tan(radians));
        }
        case 'asin': return finite(fromRadians(Math.asin(x)));
        case 'acos': return finite(fromRadians(Math.acos(x)));
        case 'atan': return finite(fromRadians(Math.atan(x)));
        case 'sqrt': return finite(Math.sqrt(x));
        case 'abs': return Math.abs(x);
        case 'ln': if (x <= 0) throw new CalculatorError('로그의 진수는 양수여야 합니다.'); return finite(Math.log(x));
        case 'log10': if (x <= 0) throw new CalculatorError('로그의 진수는 양수여야 합니다.'); return finite(Math.log10(x));
        case 'log':
          if (x <= 0 || args[1] <= 0 || args[1] === 1)
            throw new CalculatorError('로그의 진수와 밑을 확인하세요.');
          return finite(Math.log(x) / Math.log(args[1]));
        case 'exp': return finite(Math.exp(x));
        case 'floor': return Math.floor(x);
        case 'ceil': return Math.ceil(x);
        case 'round': return Math.round(x);
        case 'factorial': return factorial(x);
      }
    }
    function primary() {
      if (peek('(')) { take('('); const value = sum(); take(')'); return value; }
      const token = take();
      if (token.kind === 'number') return token.value;
      if (token.kind !== 'name') throw new CalculatorError('숫자 또는 함수를 입력하세요.');
      if (peek('(')) {
        take('(');
        const args = [];
        if (!peek(')')) {
          args.push(sum());
          while (peek(',')) { take(','); args.push(sum()); }
        }
        take(')');
        return call(token.value,args);
      }
      if (token.value === 'pi') return Math.PI;
      if (token.value === 'e') return Math.E;
      throw new CalculatorError('알 수 없는 상수입니다.');
    }
    function postfix() {
      let value = primary();
      while (peek('!') || peek('%')) {
        const operator = take().value;
        value = operator === '!' ? factorial(value) : finite(value / 100);
      }
      return value;
    }
    // Power is right-associative. Parsing its right operand through unary also
    // permits 2^-2, while keeping -2^2 equal to -(2^2), not (-2)^2.
    function power() {
      let value = postfix();
      if (peek('^') || peek('**')) { take(); value = finite(Math.pow(value,unary())); }
      return value;
    }
    function unary() {
      if (++depth > 32) { depth--; throw new CalculatorError('괄호 또는 중첩이 너무 깊습니다.'); }
      try {
        if (peek('+')) { take('+'); return unary(); }
        if (peek('-')) { take('-'); return finite(-unary()); }
        return power();
      } finally { depth--; }
    }
    function product() {
      let value = unary();
      while (peek('*') || peek('/')) {
        const operator = take().value, right = unary();
        if (operator === '/' && right === 0) throw new CalculatorError('0으로 나눌 수 없습니다.');
        value = finite(operator === '*' ? value * right : value / right);
      }
      return value;
    }
    function sum() {
      let value = product();
      while (peek('+') || peek('-')) {
        const operator = take().value, right = product();
        value = finite(operator === '+' ? value + right : value - right);
      }
      return value;
    }
    const result = sum();
    if (position !== tokens.length) throw new CalculatorError('연산자 또는 괄호를 확인하세요.');
    return finite(result);
  }
  const api = Object.freeze({evaluate,CalculatorError});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.CalculatorCore = api;
})(typeof globalThis === 'undefined' ? null : globalThis);
