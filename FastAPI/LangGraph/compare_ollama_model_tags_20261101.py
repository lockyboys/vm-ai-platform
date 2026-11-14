"""노트북 Ollama의 두 모델 이름(gemma4:latest, gemma4:e4b)이 같은 모델인지 읽기 전용으로 비교 (2026-11-01).

이유: LuckyBoys 질문 — gemma4:latest가 양자화 모델이라 e4b와 다른지 증거로 확인.
동작: GET /api/tags(이름별 digest·크기) + POST /api/show(이름별 details: format, family, parameter_size,
      quantization_level). 모델을 받거나 지우지 않는다. 주소는 config.OLLAMA_ENDPOINT(노트북 터널).
"""
import json
import urllib.request

import config  # 루트 공통 설정(일반 지침 4)

NAMES = ["gemma4:latest", "gemma4:e4b"]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 워커와 같이 프록시 미사용


def call(route, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(config.OLLAMA_ENDPOINT + route, data=data, headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=30) as r:
        return json.load(r)


tags = {m["name"]: m for m in call("/api/tags")["models"]}
out = {}
for name in NAMES:
    show = call("/api/show", {"model": name})
    out[name] = {"digest": tags.get(name, {}).get("digest"), "size_bytes": tags.get(name, {}).get("size"),
                 "details": show.get("details"),
                 "general.quantization_version": (show.get("model_info") or {}).get("general.quantization_version"),
                 "general.file_type": (show.get("model_info") or {}).get("general.file_type")}
out["same_digest"] = out[NAMES[0]]["digest"] == out[NAMES[1]]["digest"]
print(json.dumps(out, ensure_ascii=False, indent=2))
