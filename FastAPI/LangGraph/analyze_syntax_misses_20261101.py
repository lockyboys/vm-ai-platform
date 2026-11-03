"""블라인드 리뷰 '문법(syntax)' 범주 저득점 원인 분석 — 읽기 전용 (2026-11-01, LuckyBoys 요청).

배경: gemma4 12b 기본 검토 54/82 중 문법은 6/20 (e4b 4~5/20, Gemini 20/20). 모델이 커져도 문법만 거의 그대로.
가설과 확인 방법(정답 키·결과 파일만 읽음, API 호출·파일 쓰기 없음):
  H1 채점 창(앞 2,500자) 밖에서만 언급 → 정답 단서 단어의 '응답 내 첫 위치'가 2,500자 뒤인지
  H2 아예 언급 안 함 → 단서 단어가 응답 전체에 없음
  H3 언급은 했지만 채점관이 불인정 → 단서가 창 안에 있는데 0점(채점 사유 확인)
  H4 응답 잘림 → done_reason=length
출력: 표준출력 JSON(작업별 요약 + 12b 0점 문법 건 상세).
"""
import base64
import json
import re
import zlib
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
BASE = ROOT / "harness/apps/blind_review_20261027/results"
JUDGE_WINDOW = 2500  # score_blind_review_job_20261101.py 와 같은 값(채점관이 본 응답 앞부분 길이)
# 비교할 작업(제공자, job_id) — 모두 같은 82건 입력(input_sha256 092fa65b…)
JOBS = {
    "gemini_review": ("gemini", "cc319de2752c4649a13e1834a2c0c864"),
    "e4b_review": ("ollama", "a6f4e01600d6446e8d265badbda3c522"),
    "e4b_bug_focus": ("ollama", "9f534fe37fb2433194a1f36593f80e58"),
    "12b_review": ("ollama", "76508f145da54186a1794efd96b74746"),
}
STOP = {"with", "from", "that", "this", "when", "into", "than", "instead", "should", "function", "code"}


def load(provider, job_id):
    """최종 결과 파일(.attempt 제외)과 채점 파일을 blind_id 기준으로 묶는다."""
    d = BASE / provider / "jobs" / job_id
    results = {}
    for f in d.glob("*.json"):
        if f.name in ("summary.json", "score.json") or ".attempt" in f.name:
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(r, dict) and "id" in r:
            results[r["id"]] = r
    scores = {}
    for f in (d / "scoring_packages/scores").glob("*_scores.json"):
        for s in json.loads(f.read_text(encoding="utf-8")):
            scores[s["blind_id"]] = s
    return results, scores


def clue_words(desc):
    """정답 설명의 영문 식별자(4자 이상)를 단서로 쓴다(근사 판정)."""
    return {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", desc or "")} - STOP


def first_pos(text, words):
    """단서 단어가 응답에 처음 나오는 위치(없으면 None)."""
    low = text.lower()
    hits = [low.find(w) for w in words if w in low]
    return min(hits) if hits else None


pkg = json.loads(zlib.decompress(base64.b64decode("".join(
    (ROOT / "harness/apps/blind_review_judge_20261027/private_judge.b64").read_text().split()))))
key = json.loads(pkg["private_key.json"])
syntax_ids = [bid for bid, info in key.items() if info.get("category") == "syntax"]
data = {name: load(*job) for name, job in JOBS.items()}

summary, detail = {}, []
for name in JOBS:
    results, scores = data[name]
    counts = {"n": 0, "score1": 0, "H1_clue_only_after_window": 0, "H2_no_clue": 0,
              "H3_clue_in_window_but_0": 0, "H4_truncated": 0, "chars": []}
    for bid in syntax_ids:
        r, s = results.get(bid, {}), scores.get(bid, {})
        text = r.get("response") or ""
        pos = first_pos(text, clue_words(key[bid].get("description")))
        counts["n"] += 1
        counts["chars"].append(len(text))
        counts["H4_truncated"] += int(bool(r.get("truncated")) or (r.get("raw") or {}).get("done_reason") == "length")
        if s.get("score") == 1:
            counts["score1"] += 1
            continue
        if pos is None:
            counts["H2_no_clue"] += 1
        elif pos >= JUDGE_WINDOW:
            counts["H1_clue_only_after_window"] += 1
        else:
            counts["H3_clue_in_window_but_0"] += 1
        if name == "12b_review":  # 12b 0점 건 상세(원인 판독용)
            detail.append({"id": bid, "app": key[bid].get("app"), "desc": (key[bid].get("description") or "")[:200],
                           "first_clue_pos": pos, "chars": len(text), "judge_reason": (s.get("reason") or "")[:220],
                           "response_head": text[:350]})
    chars = sorted(counts.pop("chars"))
    counts["chars_median"] = chars[len(chars) // 2] if chars else None
    summary[name] = counts

print(json.dumps({"syntax_items": len(syntax_ids), "summary": summary, "12b_zero_detail": detail[:8]},
                 ensure_ascii=False, indent=1))
