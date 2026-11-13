"""[수리] 실행 → 판정 → 수리 → 재실행 루프 (2026-11-12 분리, 원본: self_repair_engine.py §3).

흐름(원본 그대로)
    실행·판정 실패 → 허용 경로 백업 → 작업문 작성 → 페르소나 수리 체인(run_chain, 대상별 scope)
    → 아무것도 못 바꿨으면 NO_CHANGE 로 중단 / 체인 검증 실패면 원복 후 다음 라운드 / STAGED 면 재실행·재판정
    → max_rounds 까지. 증빙 JSON 을 config.SELF_REPAIR['report_dir']/<대상>/repair_<KST>.json 에 남긴다.
수리는 git add 까지만 하고 커밋하지 않는다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

import json

import config as project_config  # 루트 공통 설정(일반 지침 4)
from harness.mcp.agents.persona_repair_chain import run_chain
# 기존 수리 루프의 검증된 부품 재사용(수정하지 않음): staged 확인, 백업, 원복
from harness.mcp.agents.autodiscover_self_repair import backup_sources, restore_sources, staged_change_sets
from harness.selffix.job_runner import KST, PROJECT_ROOT, _write_json, now_stamp
from harness.selffix.runner import _default_run, evaluate
from harness.selffix.target_spec import validate_params, validate_target

_SETTINGS = project_config.SELF_REPAIR


def _build_task(spec: dict, failure: dict, rounds: list[dict]) -> str:
    """수리 체인에 넘길 작업문. 대상·실패·범위만 담고 특정 사이트·대상 하드코딩을 금지한다."""
    previous = "\n".join(f"- round {r['round']}: {r['outcome']} {r.get('detail', '')}"[:300] for r in rounds) or "- 없음"
    return (f"[자기 수리 대상] {spec['name']}\n"
            f"[실패 유형] {failure['category']}\n[오류] {failure['error']}\n"
            f"[증빙(출력 끝부분)]\n{failure['evidence']}\n"
            f"[수정 허용 경로] {json.dumps(spec['scope']['allowed_paths'], ensure_ascii=False)}\n"
            f"[회귀 테스트] {json.dumps(spec['scope']['regression_tests'], ensure_ascii=False)}\n"
            f"[이전 라운드]\n{previous}\n"
            "[규칙] 원인을 찾아 허용 경로 안에서 최소 수정한다. 사이트 이름·URL·대상 이름을 코드에 하드코딩하지 않는다. "
            "테스트로 재현 후 고치고 git add 까지만 한다(커밋 금지).")


def _default_partner(task: str, round_no: int, scope: dict) -> dict:
    """기본 수리기: 페르소나 수리 체인을 대상별 scope 로 실행한다."""
    return run_chain(task, staged_fn=staged_change_sets, round_no=round_no, scope=scope)


def run_with_repair(spec: dict, params: dict, run_fn: Callable = None, partner_fn: Callable = None,
                    backup_fn: Callable = None, restore_fn: Callable = None) -> dict:
    """대상을 실행하고, 실패하면 max_rounds 까지 수리·재실행한다. 증빙 JSON 을 남긴다."""
    spec = validate_target(spec)
    params = validate_params(spec, params)
    run_fn = run_fn or _default_run
    partner_fn = partner_fn or _default_partner
    backup_fn = backup_fn or backup_sources
    restore_fn = restore_fn or restore_sources

    failure = evaluate(spec["verdict"], run_fn(spec, params), params)
    first, rounds = failure, []
    if failure is not None and _SETTINGS.get("enabled", True):
        for round_no in range(1, spec["max_rounds"] + 1):
            task = _build_task(spec, failure, rounds)
            backups = backup_fn(list(spec["scope"]["allowed_paths"]))
            try:
                report = partner_fn(task, round_no, spec["scope"])
            except Exception as error:  # noqa: BLE001 - 수리기 오류는 원복 후 다음 라운드
                restore_fn(backups)
                rounds.append({"round": round_no, "outcome": "ERROR", "detail": f"{type(error).__name__}: {error}"})
                continue
            if not staged_change_sets(report):
                # 아무것도 바꾸지 못했으면 같은 시도를 반복해도 비용만 든다 → 중단
                rounds.append({"round": round_no, "outcome": "NO_CHANGE"})
                break
            if report.get("verdict") != "PASS":
                restore_fn(backups)  # 검증을 통과하지 못한 수정은 되돌린다
                rounds.append({"round": round_no, "outcome": str(report.get("verdict", "미확인"))})
                continue
            failure = evaluate(spec["verdict"], run_fn(spec, params), params)
            rounds.append({"round": round_no, "outcome": "STAGED",
                           "detail": "OK" if failure is None else failure["error"]})
            if failure is None:
                break
    if failure is None:
        verdict_text = "OK"
    else:
        verdict_text = "REPAIR_FAILED" if rounds else "FAILED"
    result = {"target": spec["name"], "result": verdict_text, "first": first, "rounds": rounds,
              "final": failure, "checked_kst": datetime.now(KST).isoformat()}
    evidence_path = PROJECT_ROOT / str(_SETTINGS["report_dir"]) / spec["name"] / f"repair_{now_stamp()}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(evidence_path, result)
    return {**result, "evidence": str(evidence_path)}
