"""GPU 서버(turing-enigma-ai)에서 Ollama가 GPU를 쓰지 않는 원인을 읽기 전용으로 확인한다 (2026-11-01, LuckyBoys 승인 요청).

배경: harness/memory/ollama_latency_diagnose_20261101_b.json 에서 size_vram=0(GPU 적재 0%)이 확인됨.
목적: GPU 서버에서 아래 '읽기 전용' 명령만 ssh 1회로 실행해, GPU 인식 여부·점유 프로세스·Ollama 설정을 본다.
  1) nvidia-smi --query-gpu=...           : GPU 이름·메모리 사용량·사용률·드라이버 버전
  2) nvidia-smi --query-compute-apps=...  : GPU 메모리를 잡고 있는 프로세스(다른 프로세스가 VRAM을 다 쓰는지)
  3) systemctl is-active ollama            : Ollama 서비스 가동 여부(상태 조회만, 시작/정지 안 함)
  4) systemctl show ollama -p Environment  : OLLAMA_*/CUDA_VISIBLE_DEVICES 같은 환경 설정(조회만)
  5) ollama ps                             : 원격에서 본 적재 모델과 PROCESSOR(GPU/CPU) 표시
  6) journalctl -u ollama -n 200 | grep    : 최근 로그 중 GPU/CUDA/offload 관련 줄만(권한 없으면 오류 문구를 그대로 기록)
주의:
  - 원격의 파일·서비스·설정을 바꾸지 않는다. sudo는 쓰지 않는다.
  - 접속 정보는 루트 config.py의 SPS_SSH_TARGETS["gpu"]만 쓴다(하드코딩 금지, 비밀키는 경로만 참조).
  - BatchMode=yes(비밀번호 묻지 않음), StrictHostKeyChecking=yes(등록된 호스트키만 허용).
  - 결과는 harness/memory/ollama_gpu_remote_check_<run_id>.json 에 새로 저장(시작 시 running → 끝나면 최종 결과).
입력(stdin JSON): {"run_id": "<영숫자_->"}
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config  # 루트 공통 설정(일반 지침 4)

# 원격에서 실행할 읽기 전용 명령. 각 명령의 출력을 구분선으로 나눠 한 번의 ssh로 받는다.
REMOTE_COMMANDS = [
    "nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu --format=csv,noheader",
    "nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader",
    "systemctl is-active ollama",
    "systemctl show ollama -p Environment",
    "ollama ps",
    "journalctl -u ollama -n 200 --no-pager | grep -i -E 'gpu|cuda|vram|offload|library' | tail -n 40",
]
MARK = "===SPS_CMD==="  # 출력 분리용 표식


def _kst() -> str:
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()


def _write(path: Path, value: dict) -> None:
    """임시 파일에 쓴 뒤 교체(읽는 쪽이 반쯤 쓴 JSON을 보지 않게)."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    run_id = request.get("run_id")
    # run_id는 파일명에 들어가므로 영숫자·_·- 1~64자만 허용(경로 이탈 차단)
    if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id) is None:
        raise ValueError("run_id must match [A-Za-z0-9_-]{1,64}")
    path = Path(config.PROJECT_ROOT) / "harness/memory" / f"ollama_gpu_remote_check_{run_id}.json"
    if path.exists():
        raise FileExistsError(f"run_id already used: {path.name}")  # 기존 증빙 보존

    target = config.SPS_SSH_TARGETS["gpu"]
    # 각 명령 앞에 표식을 찍고 stderr도 합쳐 받는다(실패 이유도 증빙). '|| true'로 한 명령 실패가 나머지를 막지 않게 한다.
    remote = "; ".join(f"echo '{MARK} {i}'; ( {cmd} ) 2>&1 || true" for i, cmd in enumerate(REMOTE_COMMANDS))
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", f"UserKnownHostsFile={target['known_hosts']}", "-o", "ConnectTimeout=15",
           "-i", target["identity_file"], "-p", str(target["port"]),
           f"{target['user']}@{target['host']}", remote]
    result = {"run_id": run_id, "state": "running", "started_kst": _kst(),
              "host": target["host"], "remote_commands": REMOTE_COMMANDS,
              "remote_mutation": False}
    _write(path, result)
    print(json.dumps({"evidence": str(path), "state": "running"}), flush=True)
    try:
        done = subprocess.run(ssh, capture_output=True, text=True,
                              timeout=config.SPS_SSH_REQUEST_TIMEOUT_SECONDS)
        result["ssh_returncode"] = done.returncode
        result["ssh_stderr"] = done.stderr[-1500:]
        # 표식 기준으로 명령별 출력을 나눈다.
        outputs, current = {}, None
        for line in done.stdout.splitlines():
            if line.startswith(MARK):
                current = REMOTE_COMMANDS[int(line.split()[1])]
                outputs[current] = []
            elif current is not None:
                outputs[current].append(line)
        result["outputs"] = {k: "\n".join(v)[-3000:] for k, v in outputs.items()}
        result["state"] = "completed" if done.returncode == 0 else "failed"
    except Exception as exc:  # 실패도 증빙으로 남긴다
        result["state"] = "failed"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:2000]
    result["finished_kst"] = _kst()
    _write(path, result)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
