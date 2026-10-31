"""Ollama 응답 지연 원인(모델 로딩 vs 생성/GPU)을 읽기 전용으로 분리 측정한다.

목적(2026-11-01 LuckyBoys 요청): PARTNER Ollama 프로브가 178초 걸린 원인을 증거로 확인한다.
측정 항목:
  1) /api/version            : 서버 응답 여부
  2) /api/ps (호출 전)       : 모델이 이미 메모리에 올라 있었는지(콜드 스타트 여부)
  3) /api/generate (1회)     : Ollama가 직접 보고하는 단계별 시간
       load_duration         → 모델 로딩 시간
       prompt_eval_duration  → 입력(프롬프트) 처리 시간
       eval_duration         → 출력 토큰 생성 시간
  4) /api/ps (호출 후)       : size_vram / size 비율 → 100%면 전부 GPU, 낮으면 CPU로 일부 넘어감
주의:
  - 소스·DB·설정을 바꾸지 않는다. 모델을 1회 로드/생성하는 것 외에 부수효과가 없다.
  - URL·모델·대기시간은 루트 config.py 값만 사용한다(하드코딩 금지 원칙).
  - MCP 연결이 끊겨도 확인할 수 있도록 입력 run_id로 결과 파일 경로를 미리 고정하고,
    시작 즉시 state=running을 기록한 뒤 끝나면 같은 파일을 최종 결과로 원자적으로 교체한다.
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

NS = 1_000_000_000  # Ollama duration 필드는 나노초 단위


def _kst() -> str:
    """증빙 타임스탬프는 KST로 남긴다(작업 규칙)."""
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()


def _write(path: Path, value: dict) -> None:
    """임시 파일에 쓴 뒤 교체해, 읽는 쪽이 반쯤 쓴 JSON을 보지 않게 한다."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _call(base: str, route: str, timeout: float, body: dict | None = None) -> dict:
    """Ollama HTTP API 1회 호출. body가 있으면 POST, 없으면 GET."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base.rstrip("/") + route, data=data,
                                     headers={"Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    payload["_wall_seconds"] = round(time.monotonic() - started, 3)
    return payload


def _gpu_ratio(ps: dict, model: str) -> dict | None:
    """/api/ps 결과에서 대상 모델의 GPU 적재 비율을 계산한다(없으면 None=미적재)."""
    for item in ps.get("models", []):
        if item.get("name") == model or item.get("model") == model:
            size, vram = item.get("size") or 0, item.get("size_vram") or 0
            return {"size_bytes": size, "size_vram_bytes": vram,
                    "gpu_ratio_percent": round(vram * 100 / size, 1) if size else None,
                    "expires_at": item.get("expires_at")}
    return None


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    run_id = request.get("run_id")
    # run_id는 파일명에 들어가므로 영숫자·밑줄·하이픈만 허용(경로 이탈 차단).
    if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id) is None:
        raise ValueError("run_id must match [A-Za-z0-9_-]{1,64}")

    import config  # 루트 공통 설정(일반 지침 4)
    from common.common_function import resolve_ollama_base_url

    # 2026-11-01: PARTNER와 같은 규칙으로 주소를 정한다(수동 고정 또는 GPU→노트북 터널→개발 서버 순 자동 선택).
    # 어느 후보가 응답했는지(selection.tried)를 결과 파일에 남겨, 측정 대상이 어디였는지 증빙한다.
    selection = resolve_ollama_base_url(
        config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL,
        config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES,
        config.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS,
    )
    base = selection["base_url"]
    model = config.SPS_SOURCE_PARTNER_OLLAMA_MODEL
    timeout = float(config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS)
    root = Path(config.PROJECT_ROOT)
    path = root / "harness/memory" / f"ollama_latency_diagnose_{run_id}.json"
    if path.exists():
        raise FileExistsError(f"run_id already used: {path.name}")  # 기존 증빙 덮어쓰기 금지

    result = {"run_id": run_id, "state": "running", "started_kst": _kst(),
              "base_url": base, "selection": selection, "model": model, "timeout_seconds": timeout,
              "source_or_db_mutation": False}
    _write(path, result)  # 연결이 끊겨도 실행 중임을 파일로 확인 가능
    print(json.dumps({"evidence": str(path), "state": "running"}), flush=True)

    try:
        result["version"] = _call(base, "/api/version", 15)
        result["ps_before"] = _gpu_ratio(_call(base, "/api/ps", 15), model)
        result["cold_start"] = result["ps_before"] is None  # 호출 전 미적재면 콜드 스타트
        generated = _call(base, "/api/generate", timeout, {
            "model": model, "prompt": "17+25의 합만 숫자로 답하세요.",
            "stream": False, "options": {"num_predict": 32}})
        result["generate"] = {
            "wall_seconds": generated["_wall_seconds"],
            "total_seconds": round(generated.get("total_duration", 0) / NS, 3),
            "load_seconds": round(generated.get("load_duration", 0) / NS, 3),
            "prompt_eval_seconds": round(generated.get("prompt_eval_duration", 0) / NS, 3),
            "prompt_tokens": generated.get("prompt_eval_count"),
            "eval_seconds": round(generated.get("eval_duration", 0) / NS, 3),
            "eval_tokens": generated.get("eval_count"),
            "response": (generated.get("response") or "")[:200]}
        tokens, seconds = generated.get("eval_count") or 0, generated.get("eval_duration") or 0
        result["generate"]["tokens_per_second"] = round(tokens * NS / seconds, 2) if seconds else None
        result["ps_after"] = _gpu_ratio(_call(base, "/api/ps", 15), model)
        result["state"] = "completed"
    except Exception as exc:  # 실패도 증빙으로 남긴다(미확인을 성공으로 보고하지 않기)
        result["state"] = "failed"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:2000]
    result["finished_kst"] = _kst()
    _write(path, result)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
