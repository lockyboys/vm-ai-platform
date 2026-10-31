'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { chunkTextBySentence, normalizeText, splitIntoSentences } = require('../src/chunker');

test('줄바꿈을 공백으로 정규화하고 문장을 분리한다', () => {
  assert.equal(normalizeText('첫 문장.\n둘째 문장!'), '첫 문장. 둘째 문장!');
  assert.deepEqual(splitIntoSentences('첫 문장.\n둘째 문장!'), ['첫 문장.', '둘째 문장!']);
});

test('문장 중간을 자르지 않고 순번 청크를 만든다', () => {
  const text = Array.from({ length: 12 }, (_, i) => '문장 ' + (i + 1) + '입니다.').join(' ');
  const chunks = chunkTextBySentence(text, 40, 15);
  assert.ok(chunks.length > 1);
  assert.deepEqual(chunks.map(chunk => chunk.chunk_no), chunks.map((_, i) => i + 1));
  for (const chunk of chunks) assert.match(chunk.text, /[.!?。！？]$/u);
});

test('빈 텍스트와 잘못된 크기를 거부한다', () => {
  assert.deepEqual(chunkTextBySentence(''), []);
  assert.throws(() => chunkTextBySentence('내용', 0, 0), RangeError);
  assert.throws(() => chunkTextBySentence('내용', 100, 100), RangeError);
});
