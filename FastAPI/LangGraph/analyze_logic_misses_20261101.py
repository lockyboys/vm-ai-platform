"""블라인드 리뷰 '논리(logic)' 범주 놓침 분석 — 읽기 전용 (2026-11-01, LuckyBoys 요청).

배경: 12b 점검표(checklist) 69/82 중 논리 13/20, Gemini 19/20. 지난 분석(e4b)에서는 테트리스 규칙 결함을 주로 놓쳤다.
확인: ① 앱별(계산기/테트리스) 논리 점수 ② 12b가 놓친 건의 정답 설명·채점 사유 ③ 단서 단어가 응답에 있는지
      (없음=결함 미언급 / 있음=언급했지만 원인을 틀리게 짚음) — 정답 키·결과·채점 파일만 읽음(API 호출·파일 쓰기 없음).
"""
import base64
import json
import re
import zlib
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
BASE = ROOT / "haness/apps/blind_review_20261027/results"
JOBS = {"gemini_review": ("gemini", "cc319de2752c4649a13e1834a2c0c864"),
        "12b_review": ("ollama", "76508f145da54186a1794efd96b74746"),
        "12b_checklist": ("ollama", "a0ead49b5f3140c5be2ae46db4e2d0c7"),
        # 2026-11-01 ⑤(표준 규칙·관례) 추가 실험 — 앱별 논리 점수 비교용
        "12b_checklist_rules": ("ollama", "91f63317f1334ffa9558ddc056fdf68e")}
STOP = {"with", "from", "that", "this", "when", "into", "than", "instead", "should", "function", "code"}


def load(provider, job_id):
    """최종 결과(.attempt 제외)와 채점 결과를 blind_id 기준으로 읽는다."""
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


def clue_hit(text, desc):
    """정답 설명의 영문 식별자(4자 이상) 중 응답에 나온 단어 목록(근사 판정)."""
    words = {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", desc or "")} - STOP
    low = (text or "").lower()
    return sorted(w for w in words if w in low)


pkg = json.loads(zlib.decompress(base64.b64decode("".join(
    (ROOT / "haness/apps/blind_review_judge_20261027/private_judge.b64").read_text().split()))))
key = json.loads(pkg["private_key.json"])
logic_ids = [b for b, i in key.items() if i.get("category") == "logic"]
data = {n: load(*j) for n, j in JOBS.items()}

by_app = {}
for n in JOBS:
    for b in logic_ids:
        app = key[b].get("app")
        cell = by_app.setdefault(app, {}).setdefault(n, {"n": 0, "score1": 0})
        cell["n"] += 1
        cell["score1"] += int(data[n][1].get(b, {}).get("score") == 1)

misses = []
r12, s12 = data["12b_checklist"]
for b in logic_ids:
    if s12.get(b, {}).get("score") == 1:
        continue
    text = r12.get(b, {}).get("response") or ""
    misses.append({"id": b, "app": key[b].get("app"), "desc": (key[b].get("description") or "")[:220],
                   "gemini_score": data["gemini_review"][1].get(b, {}).get("score"),
                   "12b_review_score": data["12b_review"][1].get(b, {}).get("score"),
                   "clue_words_in_response": clue_hit(text, key[b].get("description")),
                   "judge_reason": (s12.get(b, {}).get("reason") or "")[:260]})

print(json.dumps({"logic_items": len(logic_ids), "by_app": by_app, "12b_checklist_misses": misses},
                 ensure_ascii=False, indent=1))
