"""블라인드 리뷰 점수 분석 — Ollama 27/82 원인 파악용, 읽기 전용 (2026-11-01, LuckyBoys 요청).

입력 파일(모두 기존 결과, API 호출 없음):
  - Ollama job a6f4e016…: 응답 결과 파일 + scoring_packages/scores/*_scores.json
  - Gemini job cc319de2…: 같은 구조
분석 항목:
  1) 범주별 점수표(두 모델)
  2) 응답 길이(문자), 출력 토큰(eval_count), 잘림 여부(done_reason=length / truncated)
  3) 채점관이 본 앞 2,500자 밖에만 결함 단서가 있었을 가능성:
     정답 키 description의 핵심 단어가 응답 '전체'에는 있는데 '앞 2,500자'에는 없는 건 수(근사치)
  4) 둘 다 맞힘/둘 다 틀림/한쪽만 맞힘 교차표, Ollama 0점 사유 샘플
결과는 표준출력 JSON으로만 낸다(파일 쓰기 없음).
"""
import base64
import json
import re
import statistics
import zlib
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
BASE = ROOT / "harness/apps/blind_review_20261027/results"
JOBS = {"ollama": "a6f4e01600d6446e8d265badbda3c522", "gemini": "cc319de2752c4649a13e1834a2c0c864"}
JUDGE_WINDOW = 2500  # 채점관이 실제로 본 응답 길이(채점 스크립트와 동일)


def load(provider):
    """결과 파일(최종본만)과 점수 파일을 blind_id 기준으로 묶는다."""
    d = BASE / provider / "jobs" / JOBS[provider]
    results = {}
    for f in d.glob("*.json"):
        if f.name in ("summary.json", "score.json") or ".attempt" in f.name:
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        results[r["id"]] = r
    scores = {}
    for f in (d / "scoring_packages/scores").glob("*_scores.json"):
        for s in json.loads(f.read_text(encoding="utf-8")):
            scores[s["blind_id"]] = s
    return results, scores


def keywords(desc):
    """정답 설명에서 단서 단어 추출(영문/숫자 토큰 4자 이상 + 연산자 기호). 근사 판정용."""
    words = {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", desc or "")}
    return words - {"with", "from", "that", "this", "when", "into", "than", "instead", "should"}


pkg = json.loads(zlib.decompress(base64.b64decode("".join(
    (ROOT / "harness/apps/blind_review_judge_20261027/private_judge.b64").read_text().split()))))
key = json.loads(pkg["private_key.json"])

data = {p: load(p) for p in JOBS}
rows = []
for bid, info in key.items():
    row = {"id": bid, "cat": info.get("category"), "desc": (info.get("description") or "")[:120]}
    for p in JOBS:
        r, s = data[p][0].get(bid, {}), data[p][1].get(bid, {})
        text = r.get("response", "") or ""
        raw = r.get("raw") or {}
        kw = keywords(info.get("description"))
        hits_full = {k for k in kw if k in text.lower()}
        hits_head = {k for k in kw if k in text[:JUDGE_WINDOW].lower()}
        row[p] = {"score": s.get("score"), "reason": (s.get("reason") or "")[:160], "chars": len(text),
                  "eval_tokens": raw.get("eval_count") or (r.get("usage") or {}).get("output_tokens"),
                  "truncated": bool(r.get("truncated")) or raw.get("done_reason") == "length",
                  "kw_total": len(kw), "kw_hit_full": len(hits_full), "kw_hit_head": len(hits_head),
                  "clue_only_after_window": bool(hits_full - hits_head) and not hits_head}
    rows.append(row)


def stat(p, pred=lambda r: True):
    sel = [r[p] for r in rows if pred(r)]
    chars = [x["chars"] for x in sel]
    return {"n": len(sel), "score": sum(1 for x in sel if x["score"] == 1),
            "chars_median": statistics.median(chars) if chars else None,
            "over_window": sum(1 for c in chars if c > JUDGE_WINDOW),
            "truncated": sum(1 for x in sel if x["truncated"]),
            "clue_only_after_window": sum(1 for x in sel if x["clue_only_after_window"])}


cats = sorted({r["cat"] for r in rows})
out = {
    "by_category": {c: {p: stat(p, lambda r, c=c: r["cat"] == c) for p in JOBS} for c in cats},
    "overall": {p: stat(p) for p in JOBS},
    "cross": {
        "both_1": sum(1 for r in rows if r["ollama"]["score"] == 1 and r["gemini"]["score"] == 1),
        "gemini_only": sum(1 for r in rows if r["ollama"]["score"] != 1 and r["gemini"]["score"] == 1),
        "ollama_only": sum(1 for r in rows if r["ollama"]["score"] == 1 and r["gemini"]["score"] != 1),
        "both_0": sum(1 for r in rows if r["ollama"]["score"] != 1 and r["gemini"]["score"] != 1)},
    "ollama_zero_by_clue": {
        "zero_and_clue_only_after_window": sum(1 for r in rows if r["ollama"]["score"] == 0 and r["ollama"]["clue_only_after_window"]),
        "zero_and_no_clue_anywhere": sum(1 for r in rows if r["ollama"]["score"] == 0 and r["ollama"]["kw_hit_full"] == 0),
        "zero_and_clue_in_window": sum(1 for r in rows if r["ollama"]["score"] == 0 and r["ollama"]["kw_hit_head"] > 0)},
    "ollama_zero_samples": [{"id": r["id"], "cat": r["cat"], "desc": r["desc"], "reason": r["ollama"]["reason"],
                             "chars": r["ollama"]["chars"]} for r in rows if r["ollama"]["score"] == 0][:12],
    "ollama_one_samples": [{"id": r["id"], "cat": r["cat"], "desc": r["desc"], "reason": r["ollama"]["reason"]}
                           for r in rows if r["ollama"]["score"] == 1][:4],
}
print(json.dumps(out, ensure_ascii=False, indent=1))
