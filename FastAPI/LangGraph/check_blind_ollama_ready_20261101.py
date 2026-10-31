"""블라인드 리뷰 Ollama 실행 전 준비 상태 확인 — 읽기 전용 (2026-11-01, LuckyBoys '설정 먼저 확인').

확인 항목:
 1) 워커가 쓰는 config 값: OLLAMA_ENDPOINT/MODEL/NUM_GPU/NUM_CTX/NUM_PREDICT/WORKERS/KEEP_ALIVE
 2) 그 주소의 /api/tags 에 워커가 찾는 모델 이름이 있는지, digest가 워커 고정값(DIGEST)과 같은지
    (blind_worker.py는 name==OLLAMA_MODEL 이고 digest 일치일 때만 시작한다)
 3) 이전 Ollama 결과 파일(성공분)의 응답 시간·출력 토큰 통계 → 82건 예상 소요 시간 추정 근거
파일·DB·설정은 바꾸지 않는다. 네트워크는 GET /api/tags 1회뿐.
"""
import json
import statistics
import urllib.request
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

WORKER_DIGEST = "dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c"  # blind_worker.py DIGEST와 동일(비교용)
RESULTS = Path(config.PROJECT_ROOT) / "haness/apps/blind_review_20261027/results/ollama"

report = {"config": {k: getattr(config, k) for k in (
    "OLLAMA_ENDPOINT", "OLLAMA_MODEL", "OLLAMA_NUM_GPU", "OLLAMA_NUM_CTX", "OLLAMA_NUM_BATCH",
    "OLLAMA_NUM_PREDICT", "OLLAMA_WORKERS", "OLLAMA_KEEP_ALIVE", "OLLAMA_TIMEOUT_SECONDS")}}
try:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 워커와 같이 프록시 미사용
    with opener.open(config.OLLAMA_ENDPOINT + "/api/tags", timeout=10) as r:
        tags = json.load(r)
    report["models"] = [{"name": m["name"], "digest": m["digest"][:12], "size_gb": round(m["size"] / 1e9, 2)}
                        for m in tags.get("models", [])]
    match = [m for m in tags.get("models", []) if m["name"] == config.OLLAMA_MODEL]
    report["worker_model_found"] = bool(match)
    report["worker_digest_match"] = bool(match) and match[0]["digest"] == WORKER_DIGEST
    report["same_digest_other_names"] = [m["name"] for m in tags.get("models", []) if m["digest"] == WORKER_DIGEST]
except Exception as error:
    report["tags_error"] = f"{type(error).__name__}: {error}"

# 이전 Ollama 결과(성공분)의 시간 통계 — 재귀로 모든 job 디렉터리를 본다.
elapsed, out_tokens, ok, fail = [], [], 0, 0
for p in RESULTS.rglob("*.json"):
    if p.name == "summary.json" or ".attempt" in p.name:
        continue
    try:
        r = json.loads(p.read_text())
    except Exception:
        continue
    if r.get("success") is True:
        ok += 1
        elapsed.append(r.get("elapsed_seconds") or 0)
        out_tokens.append((r.get("raw") or {}).get("eval_count") or 0)
    else:
        fail += 1
report["previous_ollama_results"] = {
    "success_files": ok, "failed_files": fail,
    "elapsed_median_s": round(statistics.median(elapsed), 1) if elapsed else None,
    "elapsed_max_s": round(max(elapsed), 1) if elapsed else None,
    "eval_tokens_median": statistics.median(out_tokens) if out_tokens else None,
}
print(json.dumps(report, ensure_ascii=False, indent=2))
