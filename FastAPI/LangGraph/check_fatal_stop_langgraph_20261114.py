"""LangGraph 안에서 stop_on_fatal_provider_error(SystemExit)가 그래프 전체를 멈추는지 확인 (2026-11-14).

실제 LLM은 부르지 않는다. 두 갈래로 나뉘는(병렬) 노드 중 하나가 크레딧 부족 402 오류 문장으로
safe_invoke_llm과 같은 처리를 하면, 그 뒤 노드(after)가 실행되지 않고 프로세스가 종료 코드 3으로 끝나야 한다.
기대 출력: 표시 줄 1개, "after 실행됨"이 없음, 종료 코드 = config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHILD = r'''
import sys
sys.path.insert(0, %r)
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from common.common_function import stop_on_fatal_provider_error

class S(TypedDict, total=False):
    a: int
    b: int

def credit_node(state):
    try:
        raise RuntimeError("402 RESOURCE_EXHAUSTED. Your prepayment credits are depleted.")
    except Exception as e:  # safe_invoke_llm과 같은 모양: 일반 except 안에서 정지 함수 호출
        stop_on_fatal_provider_error(str(e), "credit_node")
        return {"a": 1}

def other_node(state):
    return {"b": 1}

def after(state):
    print("after 실행됨")
    return {}

g = StateGraph(S)
g.add_node("credit_node", credit_node)
g.add_node("other_node", other_node)
g.add_node("after", after)
g.add_edge(START, "credit_node")
g.add_edge(START, "other_node")
g.add_edge(["credit_node", "other_node"], "after")
g.add_edge("after", END)
try:
    g.compile().invoke({})
except Exception as e:  # CLI main처럼 일반 예외를 잡아도 SystemExit는 빠져나가야 한다
    print("일반 예외로 잡힘(실패):", type(e).__name__, e)
print("그래프가 끝까지 실행됨(실패)")
''' % str(ROOT)

completed = subprocess.run([sys.executable, "-c", CHILD], capture_output=True, text=True, timeout=120)
print("returncode:", completed.returncode)
print("stdout:\n" + completed.stdout)
print("stderr 끝:\n" + completed.stderr[-800:])
sys.path.insert(0, str(ROOT))  # 루트 config.py를 읽기 위해
import config
ok = (completed.returncode == config.MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE
      and completed.stdout.startswith(config.MULTI_PERSONA_FATAL_PROVIDER_MARKER)
      and "after 실행됨" not in completed.stdout and "(실패)" not in completed.stdout)
print("판정:", "통과" if ok else "실패")
sys.exit(0 if ok else 1)
