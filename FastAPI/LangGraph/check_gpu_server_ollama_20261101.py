"""GPU 서버 Ollama 접속·모델 목록 읽기 전용 확인 (2026-11-01, LuckyBoys: GPU 서버 켬).

입력(stdin JSON): {"host": "<IPv4>"} — IP는 켤 때마다 바뀌므로 입력으로 받는다(코드에 고정하지 않음).
동작: GET http://<host>:11434/api/version, /api/tags 만 호출. 모델 받기·삭제·실행 없음.
      각 모델의 이름·digest·크기·양자화를 출력해, 블라인드 워커 고정 지문(dc35e8d9c606…)과 같은지 본다.
"""
import ipaddress
import json
import sys
import urllib.request

WORKER_DIGEST = "dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c"  # blind_worker.py DIGEST(비교용)

# 2026-11-01: 개발서버→GPU ssh 터널(127.0.0.1:11436)도 확인할 수 있게 port 입력을 추가한다.
#             허용 포트는 11434(직접)·11436(터널)만 — 그 밖의 값은 거부(잘못된 입력 방지).
request = json.loads(sys.stdin.read() or "{}")
host = request.get("host", "")
port = request.get("port", 11434)
ipaddress.IPv4Address(host)  # 잘못된 입력(IP 아님)은 여기서 예외로 중단 — URL 조작 방지
if port not in (11434, 11436):
    raise ValueError(f"port must be 11434 or 11436, got {port!r}")
base = f"http://{host}:{port}"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
out = {"base": base}
for route in ("/api/version", "/api/tags"):
    try:
        with opener.open(base + route, timeout=8) as r:
            out[route] = json.load(r)
    except Exception as error:  # 방화벽·바인딩(127.0.0.1)·서비스 꺼짐 등을 그대로 기록
        out[route] = {"error": f"{type(error).__name__}: {error}"}
models = (out.get("/api/tags") or {}).get("models") or []
# config.BLIND_REVIEW_MODEL_DIGESTS에 넣을 수 있게 digest 전체(64자)를 출력한다.
out["models"] = [{"name": m.get("name"), "digest": m.get("digest") or "", "size_gb": round((m.get("size") or 0) / 1e9, 2),
                  "quant": (m.get("details") or {}).get("quantization_level"),
                  "params": (m.get("details") or {}).get("parameter_size"),
                  "same_as_worker_digest": m.get("digest") == WORKER_DIGEST} for m in models]
out.pop("/api/tags", None)
print(json.dumps(out, ensure_ascii=False, indent=2))
