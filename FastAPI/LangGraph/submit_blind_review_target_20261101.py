"""블라인드 리뷰 job 제출(실행 대상·모델 지정) — 2026-11-01 LuckyBoys GPU 서버 실험.

왜 필요한가: sps-harness.service 재시작 후에도 MCP 도구 submit_blind_review 의 입력 목록이
  옛 형태(ollama_target·ollama_model 없음)로 보여, 그대로 부르면 값이 무시되어 노트북으로 실행될 위험이 있다.
  그래서 같은 함수(haness.mcp.tools.blind_review_jobs_v2.submit)를 이 스크립트로 직접 부른다(제출 로직 중복 없음).

입력(stdin JSON):
  {"provider": "ollama", "prompt_variant": "review"|"bug_focus",
   "ollama_target": "laptop"|"gpu", "ollama_model": "<config.BLIND_REVIEW_MODEL_DIGESTS 이름>", "dry_run": true|false}
동작:
  dry_run=true  → 값 검증 + 대상 Ollama /api/tags 에서 모델 지문 일치 확인만(프로세스 띄우지 않음, LLM 호출 없음)
  dry_run=false → jobs.submit(...) 호출 → request.json(job_id·pid) 출력. 워커는 분리 실행되어 이 스크립트가 끝나도 계속 돈다.
"""
import json
import sys
import urllib.request

import config
from haness.mcp.tools import blind_review_jobs_v2 as jobs

args = json.loads(sys.stdin.read() or "{}")
provider = args.get("provider", "ollama")
variant = args.get("prompt_variant", "")
target = args.get("ollama_target", "")
model = args.get("ollama_model", "")
dry_run = args.get("dry_run", True)
if not isinstance(dry_run, bool):
    raise ValueError("dry_run must be true or false")  # "false" 문자열 등으로 실수 실행되지 않게

# 실행 전 검증(submit 과 같은 기준): 목록에 없는 값은 여기서 바로 거부
if variant and variant not in config.BLIND_REVIEW_PROMPTS:
    raise ValueError(f"unknown prompt_variant: {variant!r}")
if target and target not in config.BLIND_REVIEW_OLLAMA_ENDPOINTS:
    raise ValueError(f"unknown ollama_target: {target!r}")
if model and model not in config.BLIND_REVIEW_MODEL_DIGESTS:
    raise ValueError(f"unknown ollama_model: {model!r}")

if dry_run:
    # 대상 서버에 그 모델이 실제로 있고 지문이 맞는지만 읽기 전용으로 확인
    endpoint = config.BLIND_REVIEW_OLLAMA_ENDPOINTS[target or config.BLIND_REVIEW_DEFAULT_OLLAMA_TARGET]
    want = model or config.OLLAMA_MODEL
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 로컬 터널이므로 프록시 우회
    with opener.open(endpoint + "/api/tags", timeout=8) as response:
        tags = json.load(response)
    found = next((m for m in tags.get("models", []) if m.get("name") == want), None)
    print(json.dumps({"dry_run": True, "endpoint": endpoint, "model": want, "prompt_variant": variant or config.BLIND_REVIEW_DEFAULT_PROMPT,
                      "model_found": found is not None,
                      "digest_match": bool(found) and found.get("digest") == config.BLIND_REVIEW_MODEL_DIGESTS[want]},
                     ensure_ascii=False))
else:
    req = jobs.submit(provider, prompt_variant=variant, ollama_target=target, ollama_model=model)
    print(json.dumps(req, ensure_ascii=False))
