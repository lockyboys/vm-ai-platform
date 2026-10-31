'use strict';

/**
 * PDF 추출 텍스트를 문장 경계 기준으로 청킹한다.
 * 줄바꿈을 정규화하고 문장을 온전히 유지하면서 1,000자·200자 중복을 적용한다.
 */
function normalizeText(text) {
  if (typeof text !== 'string') throw new TypeError('text must be a string');
  return text.replace(/\s+/g, ' ').trim();
}

function splitIntoSentences(text) {
  const normalized = normalizeText(text);
  if (!normalized) return [];
  return normalized
    .split(/(?<=[.!?。！？])\s+/u)
    .map(sentence => sentence.trim())
    .filter(Boolean);
}

function chunkTextBySentence(text, chunkSize = 1000, overlapSize = 200) {
  if (!Number.isInteger(chunkSize) || chunkSize <= 0) {
    throw new RangeError('chunkSize must be a positive integer');
  }
  if (!Number.isInteger(overlapSize) || overlapSize < 0 || overlapSize >= chunkSize) {
    throw new RangeError('overlapSize must be an integer from 0 to chunkSize - 1');
  }

  const sentences = splitIntoSentences(text);
  const chunks = [];
  let start = 0;

  while (start < sentences.length) {
    const selected = [];
    let length = 0;
    let end = start;

    while (end < sentences.length) {
      length += (selected.length ? 1 : 0) + sentences[end].length;
      selected.push(sentences[end]);
      end += 1;
      if (length >= chunkSize) break;
    }

    const chunkText = selected.join(' ');
    chunks.push({
      chunk_no: chunks.length + 1,
      text: chunkText,
      char_count: chunkText.length,
      overlap_from_previous: chunks.length === 0 ? 0 : Math.min(overlapSize, chunkText.length),
    });

    if (end >= sentences.length) break;

    let overlapLength = 0;
    let overlapStart = end;
    for (let index = end - 1; index >= start; index -= 1) {
      overlapLength += sentences[index].length + (overlapLength ? 1 : 0);
      overlapStart = index;
      if (overlapLength >= overlapSize) break;
    }

    // 목표 크기보다 긴 단일 문장은 반복하지 않고 다음 문장으로 전진한다.
    start = overlapStart <= start ? end : overlapStart;
  }

  return chunks;
}

module.exports = { normalizeText, splitIntoSentences, chunkTextBySentence };
