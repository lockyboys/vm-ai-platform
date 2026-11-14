"""실제 공개 PDF와 LLM을 사용해 시험용 복사본의 오류 생성→수정을 검증한다.

운영 파일/설정은 쓰지 않는다. 에이전트·도구는 이 시험 소스 내부에 정의하며,
운영 스니퍼의 source_patch 함수를 그대로 추출해 기존 검증 모듈을 호출한다.
새로운 서비스/자동 커밋/외부 사이트 수정은 수행하지 않는다.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Annotated

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

URL = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
PROTECTED = (
    "FastAPI/LangGraph/sps_main_orchestrator.py",
    "FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py",
    "haness/source_repair.py", "config.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_pure_function(source):
    """실험용 생성 소스는 입출력 없는 PDF 판정 함수 하나로 제한한다."""
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("판정 함수 하나만 허용")
    function = tree.body[0]
    if function.name != "validate_document" or function.decorator_list:
        raise ValueError("함수명/데코레이터 불일치")
    if len(function.args.args) != 1 or function.args.args[0].arg != "payload":
        raise ValueError("payload 인자 하나만 허용")
    permitted = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
                 ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.Compare,
                 ast.In, ast.NotIn, ast.Eq, ast.NotEq, ast.Call, ast.Attribute,
                 ast.Name, ast.Load, ast.Constant, ast.Subscript, ast.Slice,
                 ast.USub, ast.If, ast.IfExp, ast.Expr)
    for node in ast.walk(tree):
        if not isinstance(node, permitted):
            raise ValueError("허용하지 않은 구문")
        if isinstance(node, ast.Name) and node.id not in {"payload", "bytes", "bool"}:
            raise ValueError("허용하지 않은 이름")
        if isinstance(node, ast.Attribute) and node.attr not in {"startswith", "endswith", "rstrip", "strip"}:
            raise ValueError("허용하지 않은 메서드")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Attribute):
            raise ValueError("payload 메서드 호출만 허용")
        if isinstance(node, ast.Call):
            root = node.func.value
            while isinstance(root, (ast.Call, ast.Attribute, ast.Subscript)):
                root = root.func.value if isinstance(root, ast.Call) else root.value
            if not isinstance(root, ast.Name) or root.id != "payload":
                raise ValueError("payload 외 호출 금지")
    return tree


async def trial():
    import config
    import httpx
    import haness.source_repair as repair
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import StateGraph, START, END, MessagesState
    from langgraph.prebuilt import ToolNode

    before = {name: digest(ROOT / name) for name in PROTECTED}
    report = {"success": False, "site": URL, "events": [], "production_unchanged": None}
    folder = ROOT / "harness/memory/source_repairs"
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder / ("live_trial_" + __import__("uuid").uuid4().hex + ".json")
    original_settings = repair.config
    try:
        async with httpx.AsyncClient(verify=True, follow_redirects=True, timeout=20) as client:
            response = await client.get(URL)
            response.raise_for_status()
        payload = response.content
        if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload[-1500:]:
            raise ValueError("공식 시험 문서가 정상 PDF가 아님")
        report["http"] = {"status": response.status_code, "bytes": len(payload),
                          "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory(prefix="sps_live_repair_") as directory:
            work = Path(directory)
            source = work / "trial_validator.py"
            source.write_text("def validate_document(payload):\n    return payload.startswith(b'%PDF-') and b'%%EOF' in payload[-1500:]\n", encoding="utf-8")
            (work / "sample.pdf").write_bytes(payload)
            # 실험 전용 저장소에만 기준 커밋을 만든다. 운영 Git은 읽기만 한다.
            def commit_fixture(message):
                subprocess.run(["git", "-C", str(work), "add", "trial_validator.py"], check=True,
                               capture_output=True)
                subprocess.run(["git", "-C", str(work), "-c", "user.name=Live Repair Test",
                    "-c", "user.email=repair-test@example.invalid", "commit", "-qm", message],
                    check=True, capture_output=True)
            subprocess.run(["git", "init", "-q", str(work)], check=True, capture_output=True)
            commit_fixture("test: preserve original fixture")
            trusted_test = '''import ast, pathlib, unittest
class LivePDFRegression(unittest.TestCase):
    def setUp(self):
        namespace = {}
        exec(compile(pathlib.Path(SOURCE_PATH).read_text(), SOURCE_PATH, 'exec'), namespace)
        self.check = namespace['validate_document']
    def test_live_official_pdf(self):
        self.assertTrue(self.check(pathlib.Path(SOURCE_PATH).with_name('sample.pdf').read_bytes()))
    def test_html_is_not_pdf(self):
        self.assertFalse(self.check(b'<html>not a PDF</html>'))
    def test_truncated_pdf(self):
        self.assertFalse(self.check(b'%PDF-1.7\\ntruncated'))
    def test_missing_pdf_header(self):
        self.assertFalse(self.check(b'garbage\\n%%EOF'))
'''
            # 검증 후보는 별도 임시 폴더에 있으므로 실제 PDF의 고정 절대 경로를 사용한다.
            trusted_test = trusted_test.replace(
                "pathlib.Path(SOURCE_PATH).with_name('sample.pdf')",
                "pathlib.Path(" + repr(str(work / "sample.pdf")) + ")")
            repair.config = SimpleNamespace(
                BASE_DIR=work, SPS_SOURCE_REPAIR_ALLOWED_PATHS=("trial_validator.py",),
                SPS_SOURCE_REPAIR_MAX_BYTES=config.SPS_SOURCE_REPAIR_MAX_BYTES,
                SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS=config.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS,
                SPS_SOURCE_REPAIR_AUDIT_DIR="audit")
            injected = False
            applied = False
            namespace = {"tool": tool, "asyncio": asyncio}
            tree = ast.parse((ROOT / PROTECTED[1]).read_text())
            originals = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and node.name in {"source_patch", "read_repair_source"}]
            if len(originals) != 2:
                raise RuntimeError("운영 스니퍼 도구 2개를 찾지 못함")
            exec(compile(ast.Module(body=originals, type_ignores=[]), "production_tools", "exec"), namespace)

            @tool
            def inject_test_fault(faulty_source: str) -> dict:
                """시험 복사본의 판정 함수에 오류를 한 번 넣고 실제 PDF로 실패를 재현합니다."""
                nonlocal injected
                if injected:
                    raise ValueError("오류 주입은 한 번만 허용")
                validate_pure_function(faulty_source)
                values = {}
                exec(compile(faulty_source, "fault", "exec"), {"__builtins__": {}}, values)
                observed = values["validate_document"](payload)
                if observed is not False:
                    raise ValueError("정상 PDF를 False로 판정하는 오류가 필요")
                repair._git_checkpoint(source)
                source.write_text(faulty_source, encoding="utf-8")
                commit_fixture("test: preserve LLM injected fault before repair")
                injected = True
                report["events"].append({"tool": "inject_test_fault", "actual_pdf_observed": False,
                                         "expected": True, "fault_sha256": digest(source)})
                return {"fault_reproduced": True, "path": "trial_validator.py", "source": faulty_source,
                        "sha256": digest(source), "regression_test": "server-fixed four unittest cases",
                        "git_checkpoint": repair._git_checkpoint(source),
                        "expected_behavior": "PDF header %PDF- and %%EOF in last 1500 bytes"}

            @tool
            async def source_patch(file_path: str, old_code: str, new_code: str,
                                   expected_sha256: str, dry_run: bool = True) -> dict:
                """운영 source_patch를 호출합니다. 시험 회귀 테스트는 서버가 고정하여 전달합니다."""
                return await namespace["source_patch"].ainvoke({
                    "file_path": file_path, "old_code": old_code, "new_code": new_code,
                    "expected_sha256": expected_sha256, "dry_run": dry_run,
                    "regression_test": trusted_test})

            async def agent_node(state: MessagesState):
                message = await model.ainvoke(state["messages"])
                # 테스트/후보 검증 규칙은 모델이 변경할 수 없다.
                for call in message.tool_calls:
                    if call["name"] == "source_patch":
                        args = call["args"]
                        if not injected or args.get("file_path") != "trial_validator.py":
                            raise ValueError("시험 복사본 외 수정 요청")
                        if args.get("old_code") != source.read_text():
                            raise ValueError("전체 원문과 일치하는 패치 필요")
                        validate_pure_function(args["new_code"])
                    report["events"].append({"tool_requested": call["name"],
                        "dry_run": call.get("args", {}).get("dry_run")})
                return {"messages": [message]}

            def after_agent(state):
                return "tools" if state["messages"][-1].tool_calls else END

            def after_tools(state):
                nonlocal applied
                for message in reversed(state["messages"]):
                    if getattr(message, "type", "") != "tool":
                        break
                    if getattr(message, "name", "") == "source_patch":
                        result = json.loads(message.content)
                        report["events"].append({"tool": "source_patch", "result": result})
                        if result.get("applied"):
                            applied = True
                            return END
                return "agent"

            tools = [inject_test_fault, namespace["read_repair_source"], source_patch]
            model = ChatGoogleGenerativeAI(model=config.SPS_MAIN_ORCHESTRATOR_MODEL,
                temperature=0, timeout=20, max_retries=0, max_output_tokens=4096).bind_tools(tools)
            builder = StateGraph(MessagesState)
            builder.add_node("agent", agent_node)
            builder.add_node("tools", ToolNode(tools))
            builder.add_edge(START, "agent")
            builder.add_conditional_edges("agent", after_agent, {"tools": "tools", END: END})
            builder.add_conditional_edges("tools", after_tools, {"agent": "agent", END: END})
            graph = builder.compile()
            prompt = '''허가된 오류 주입/자동 수정 통합 시험이다. 운영 소스와 외부 사이트는 수정하지 않는다.
먼저 inject_test_fault로 def validate_document(payload): 함수 하나를 작성해 주입하라.
오류는 PDF 헤더를 b'PDF-'로 잘못 비교하는 한 글자 누락으로 만들고 EOF 검사도 유지하라.
그 다음 반환된 git_checkpoint.ready가 True인지 반드시 확인하라.
원문/sha256과 실패 증거를 확인한 뒤 source_patch로 해당 함수를 고쳐라.
회귀 테스트는 서버가 고정하여 도구에 전달하므로 변경할 수 없다. old_code는 전체 원문이다.
정상 PDF는 payload.startswith(b'%PDF-') 및 b'%%EOF' in payload[-1500:] 조건을 모두 만족해야 한다.
반드시 동일 수정안으로 dry_run=True가 성공한 뒤 dry_run=False를 호출하라.
각 도구 호출은 직전 도구 응답을 받은 뒤 한 개씩 수행하라. 말로 완료를 주장하지 말고 실제 도구를 실행하라.'''
            await asyncio.wait_for(graph.ainvoke({"messages": [SystemMessage(content=prompt),
                HumanMessage(content="공식 사이트 PDF 조회 완료. 오류를 직접 만들고 재현·수정·실행하라.")]},
                config={"recursion_limit": 14}), timeout=75)
            report["injected"] = injected
            report["applied"] = applied
            if applied:
                # 새 namespace로 다시 로드하여 새 워커 반영과 같은 조건을 검증한다.
                fixed = {}
                validate_pure_function(source.read_text())
                exec(compile(source.read_text(), str(source), "exec"), {"__builtins__": {}}, fixed)
                report["reloaded_actual_pdf_valid"] = fixed["validate_document"](payload) is True
                report["after_sha256"] = digest(source)
                report["fixed_source"] = source.read_text()
                report["fault_backups"] = [path.name for path in work.glob("*BACKUP*")]
            report["success"] = bool(injected and applied and report.get("reloaded_actual_pdf_valid"))
    except Exception as error:
        report["error_type"] = type(error).__name__
        from haness.mcp.tools.multi_persona_tools import _mask_secrets
        report["error_message"] = _mask_secrets(str(error))[:500]
    finally:
        repair.config = original_settings
        report["production_unchanged"] = all(digest(ROOT / name) == value for name, value in before.items())
        report["success"] = report["success"] and report["production_unchanged"]
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**report, "report_path": str(report_path.relative_to(ROOT))}, ensure_ascii=False))


def main():
    if sys.argv[1:] == ["--worker"]:
        asyncio.run(trial())
        return
    from haness.mcp.tools.multi_persona_tools import _systemd_command, _mask_secrets
    unit, command = _systemd_command(["-m", "haness.tests.live_source_repair_trial", "--worker"], 110, "live-repair")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=115)
    print(_mask_secrets(result.stdout))
    if result.returncode:
        print(json.dumps({"worker_returncode": result.returncode,
                          "error": _mask_secrets(result.stderr[-2000:])}))


if __name__ == "__main__":
    main()
