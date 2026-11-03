// Independent acceptance contract: tests are never rewritten by the implementation model.
const test=require('node:test'),assert=require('node:assert/strict');
const {evaluate}=require('../engine.js');
function close(actual,expected,label){assert.ok(Number.isFinite(actual),label);assert.ok(Math.abs(actual-expected)<=1e-10*Math.max(1,Math.abs(expected)),`${label}: ${actual} != ${expected}`);}
const valid=[
 ['2+3*4',14],['(2+3)*4',20],['2^3^2',512],['2**3',8],['-2^2',-4],
 ['(-2)^2',4],['2^-2',.25],['-3!',-6],['2^3!',64],['(2^3)!',40320],
 ['1/4',.25],['.5+.25',.75],['1e3+1e-3',1000.001],['0.1+0.2',.3],
 ['sqrt(16)',4],['abs(-7)',7],['ln(e)',1],['log10(1000)',3],['log(8,2)',3],
 ['exp(0)',1],['sin(30)',.5],['cos(60)',.5],['tan(45)',1],['SIN(30)',.5],
 ['asin(0.5)',30],['acos(0.5)',60],['atan(1)',45],['factorial(5)',120],['0!',1],
 ['sin(30)+sqrt(16)',4.5],['pi*2',2*Math.PI],['π',Math.PI],['2×3+8÷4−1',7],
 ['50%',.5],['200*10%',20],['200+10%',200.1],['(-50)%',-.5],['5!',120],
 ['floor(-1.2)',-2],['ceil(-1.2)',-1],['round(1.4)',1],['sqrt(0)',0],
 ['170!',7.257415615307994e306],['cos(180)',-1],['sin(-90)',-1],['3 + +2',5],
];
for(const [expr,want] of valid)test('calculate '+expr,()=>close(evaluate(expr,'deg'),want,expr));
test('default angle mode is degrees',()=>close(evaluate('sin(30)'),.5,'default'));
test('radian mode and inverse conversions',()=>{
 close(evaluate('sin(pi/2)','rad'),1,'sin rad');close(evaluate('asin(1)','rad'),Math.PI/2,'asin rad');
 close(evaluate('tan(pi/4)','rad'),1,'tan rad');
});
for(const expr of [
 '1/0','1/(-0)','sqrt(-1)','ln(0)','log(-1,2)','log(10,1)','log(10,-2)',
 'factorial(-1)','factorial(1.5)','171!','factorial(1000000)',
 'tan(90)','tan(270)','asin(2)','acos(-2)','(-1)^0.5','1e309','exp(10000)','10^10000',
 'unknown(1)','unknown','sin()','sin(1,2)','sqrt(1,2)','log(1)',
 '', ' ', '1+', '(1+2','1+2)','1..2','2(3)','0x10','1_000',
 "__import__('os')",'process.exit()','globalThis','Math.sin(1)','constructor.constructor(1)',
 'eval(1)','[1,2]','{x:1}','1;2','1=2','`abc`','Infinity','NaN',
])test('reject '+JSON.stringify(expr),()=>assert.throws(()=>evaluate(expr,'deg'),Error));
test('reject invalid angle mode',()=>assert.throws(()=>evaluate('1','bad'),Error));
test('reject non-string expressions',()=>{for(const v of [null,undefined,3,{},[]])assert.throws(()=>evaluate(v),Error);});
test('bound input size',()=>assert.throws(()=>evaluate('1+'.repeat(1000)+'1'),Error));
test('bound nested parser recursion',()=>assert.throws(()=>evaluate('('.repeat(60)+'1'+')'.repeat(60)),Error));
test('bound unary recursion',()=>assert.throws(()=>evaluate('-'.repeat(100)+'1'),Error));

// Large finite DEG inputs must preserve periodicity without conversion overflow.
// Expected values use reduced, ordinary angles; RAD semantics remain unchanged.
for (const [expression,expected] of [
 ['sin(1e308)',Math.sin(296*Math.PI/180)],
 ['cos(1e308)',Math.cos(296*Math.PI/180)],
 ['tan(1e308)',Math.tan(296*Math.PI/180)],
 ['sin(-1e308)',Math.sin(-296*Math.PI/180)],
 ['cos(-1e308)',Math.cos(-296*Math.PI/180)],
 ['tan(-1e308)',Math.tan(-296*Math.PI/180)],
 ['sin(360000000030)',.5],
 ['cos(360000000060)',.5],
 ['tan(360000000045)',1],
]) test('large degrees '+expression,()=>close(evaluate(expression,'deg'),expected,expression));
test('large radian input is not reduced in degrees',()=>close(evaluate('sin(1e308)','rad'),Math.sin(1e308),'large rad'));
