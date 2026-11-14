"""PARTNER 실모델 프로브의 대기 시간이 루트 config.py 값을 따르는지 검증한다.

배경(2026-10-31): probe_partner_providers_20261025.py가 asyncio.wait_for(..., timeout=90)로
하드코딩되어 Ollama(설정상 300초 대기)가 응답하기 전에 TimeoutError로 끊겼다.
이 테스트는 모델·네트워크를 호출하지 않고 소스 구조만 정적으로 검사한다.
"""
import ast
from pathlib import Path

import config

# 검사 대상 프로브 소스(프로젝트 루트 기준 상대 경로)
PROBE = Path(config.PROJECT_ROOT) / "haness/scripts/probe_partner_providers_20261025.py"


def _wait_for_timeout_nodes():
    """프로브 안의 모든 asyncio.wait_for(...) 호출에서 timeout 키워드 값 노드를 모은다."""
    tree = ast.parse(PROBE.read_text(encoding="utf-8"))
    nodes = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "wait_for"):
            nodes.extend(k.value for k in node.keywords if k.arg == "timeout")
    return nodes


def test_probe_has_wait_for_timeout():
    # 대기 시간 자체가 사라지면(무한 대기) 안 된다.
    assert _wait_for_timeout_nodes(), "wait_for timeout must exist"


def test_probe_timeout_is_not_hardcoded_number():
    # 재현 테스트: 숫자 상수(예: 90)는 허용하지 않는다.
    assert not any(isinstance(n, ast.Constant) for n in _wait_for_timeout_nodes())


def test_probe_timeout_reads_partner_config():
    # 2026-11-01 변경(LuckyBoys 승인): 제공자별 설정을 고르는 timeout_for(config, provider) 호출이어야 한다.
    # 실제 설정 이름 선택(GEMINI/OLLAMA)은 test_probe_partner_gemini_timeout_runfile_20261101.py가 검증한다.
    calls = [n for n in _wait_for_timeout_nodes()
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "timeout_for"]
    assert calls, "wait_for timeout must come from timeout_for(config, provider)"


def test_config_timeout_is_positive():
    # 잘못된 설정값(0 이하)이면 프로브가 즉시 실패하므로 설정 자체도 검증한다.
    assert float(config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS) > 0
