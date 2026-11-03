"""입력 앞부분 잘림(num_ctx 초과) 가설 확인 — 읽기 전용 (2026-11-01, LuckyBoys: 문법 6/20 원인 파악).

가설: 입력(지시문+소스)이 num_ctx(8192 토큰)를 넘으면 Ollama가 '앞쪽' 토큰을 잘라낸다.
      문법 결함은 소스 상단에 주입되어(채점 사유: "코드 상단에 주입된") 모델이 결함 줄을 아예 못 볼 수 있다.
확인: 결과 파일 raw.prompt_eval_count(모델이 실제로 읽은 입력 토큰 수)와 소스 길이, 결함 위치(소스 앞쪽 비율).
      prompt_eval_count 가 num_ctx 부근에 붙어 있으면 잘림, 훨씬 작으면 잘림 아님.
출력: 표준출력 JSON(범주·앱별 요약). API 호출·파일 쓰기 없음.
"""
import base64
import json
import statistics
import zlib
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
APP = ROOT / "harness/apps/blind_review_20261027"
JOBS = {"e4b_review": "a6f4e01600d6446e8d265badbda3c522", "12b_review": "76508f145da54186a1794efd96b74746"}

inputs = {i["id"]: i for i in json.loads(zlib.decompress(base64.b64decode((APP / "blind_inputs.b64").read_text())))}
pkg = json.loads(zlib.decompress(base64.b64decode("".join(
    (ROOT / "harness/apps/blind_review_judge_20261027/private_judge.b64").read_text().split()))))
key = json.loads(pkg["private_key.json"])

out = {"num_ctx": config.OLLAMA_NUM_CTX}
for name, job in JOBS.items():
    groups = {}
    for bid, info in key.items():
        p = APP / "results/ollama/jobs" / job / f"{bid}.json"
        if not p.exists():
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        raw = r.get("raw") or {}
        src = inputs[bid]["source"]
        fault_at = src.find("__fault")  # 주입 표식(채점 사유에 나온 이름). 없으면 -1 → 위치 미확인
        g = groups.setdefault(f"{info.get('category')}/{info.get('app')}", {"n": 0, "prompt_tokens": [], "src_chars": [], "fault_pos_ratio": []})
        g["n"] += 1
        g["prompt_tokens"].append(raw.get("prompt_eval_count") or 0)
        g["src_chars"].append(len(src))
        if fault_at >= 0:
            g["fault_pos_ratio"].append(round(fault_at / len(src), 3))
    summary = {}
    for k, g in sorted(groups.items()):
        t = g["prompt_tokens"]
        summary[k] = {"n": g["n"], "prompt_tokens_min": min(t), "prompt_tokens_max": max(t),
                      "at_or_over_ctx": sum(1 for x in t if x >= config.OLLAMA_NUM_CTX - 64),
                      "src_chars_median": statistics.median(g["src_chars"]),
                      "fault_marker_found": len(g["fault_pos_ratio"]),
                      "fault_pos_ratio_median": statistics.median(g["fault_pos_ratio"]) if g["fault_pos_ratio"] else None}
    out[name] = summary
print(json.dumps(out, ensure_ascii=False, indent=1))
