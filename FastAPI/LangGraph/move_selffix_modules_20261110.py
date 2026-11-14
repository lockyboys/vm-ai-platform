"""스스로 고치는 모듈 3개를 harness/selffix/ 한 곳으로 모으는 스크립트 (2026-11-10, LuckyBoys 선택).

이동
  harness/mcp/tools/auto_apply.py                      → harness/selffix/auto_apply.py
  common/llm_provider.py                               → harness/selffix/llm_provider.py
  FastAPI/LangGraph/multi_persona/review_contract.py   → harness/selffix/review_contract.py
예전 위치에는 '연결 파일'(sys.modules 별칭)을 남겨, 예전 import 경로를 쓰는 코드·테스트도 같은 모듈 객체를 받는다
(monkeypatch 대상도 동일하므로 테스트가 깨지지 않는다).
직접 import하던 도구·CLI 5개는 새 경로로 바꾼다. review_contract의 저장소 루트 계산은 폴더 깊이가 바뀌므로
config.PROJECT_ROOT를 쓰도록 바꾼다. 기본은 dry-run, *_execute.py로 실행할 때만 실제로 바꾼다.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
NEW_PKG = "harness/selffix"
MOVES = {
    "harness/mcp/tools/auto_apply.py": ("auto_apply.py", "harness.selffix.auto_apply"),
    "common/llm_provider.py": ("llm_provider.py", "harness.selffix.llm_provider"),
    "FastAPI/LangGraph/multi_persona/review_contract.py": ("review_contract.py", "harness.selffix.review_contract"),
}
# 새 경로로 import를 바꿀 파일과 (예전 문자열, 새 문자열)
IMPORT_FIXES = {
    "harness/mcp/tools/multi_persona_tools.py": [
        ("from harness.mcp.tools import auto_apply", "from harness.selffix import auto_apply")],
    "harness/mcp/tools/apply_proposal_tools.py": [
        ("from FastAPI.LangGraph.multi_persona.review_contract import", "from harness.selffix.review_contract import"),
        ("from harness.mcp.tools import auto_apply", "from harness.selffix import auto_apply")],
    "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py": [
        ("from FastAPI.LangGraph.multi_persona.review_contract import", "from harness.selffix.review_contract import"),
        ("from common.llm_provider import", "from harness.selffix.llm_provider import")],
    "FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py": [
        ("from FastAPI.LangGraph.multi_persona.review_contract import", "from harness.selffix.review_contract import")],
}
ROOT_FIX = ("_parents = Path(__file__).resolve().parents\n"
            "_DEFAULT_PROJECT_ROOT = _parents[3] if len(_parents) > 3 else _parents[-1]\n")
ROOT_NEW = ("# 2026-11-10: harness/selffix/로 옮기며 폴더 깊이가 바뀌어 parents[N] 대신 루트 config.py 값을 쓴다.\n"
            "import config as _project_config  # noqa: E402\n"
            "_DEFAULT_PROJECT_ROOT = Path(_project_config.PROJECT_ROOT).resolve()\n")
INIT = ('"""스스로 고치는 기능 모음 (2026-11-10).\n\n'
        "- auto_apply: 백업 → 적용 → 테스트 → 실패 시 되돌림\n"
        "- llm_provider: Gemini·ChatGPT·Claude·Ollama 모델 생성\n"
        "- review_contract: 리뷰 답변 형식·import 실존·코드 생략 검사\n"
        '⚠ test_paths 없이 자동 적용하면 문법만 맞아도 원본이 바뀐다(auto_apply 헤더 참고).\n"""\n')


def _shim(new_module: str) -> str:
    return ('"""예전 import 경로 호환용 연결 파일 (2026-11-10). 실제 코드는 ' + new_module + '에 있다.\n\n'
            "sys.modules를 실제 모듈로 바꿔, 예전 경로로 import해도 같은 모듈 객체(함수·monkeypatch 대상)를 받는다.\n"
            '"""\nimport importlib\nimport sys\n\n'
            f'sys.modules[__name__] = importlib.import_module("{new_module}")\n')


def _tracked(rel: str) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT,
                          capture_output=True).returncode == 0


def main() -> None:
    execute = "--execute" in sys.argv[1:]
    report = {"mode": "execute" if execute else "dry_run", "moves": [], "import_fixes": [], "root_fix": False}
    for old, (name, _) in MOVES.items():
        if (ROOT / NEW_PKG / name).exists():
            raise FileExistsError(f"{NEW_PKG}/{name} already exists")
        report["moves"].append({"from": old, "to": f"{NEW_PKG}/{name}", "tracked": _tracked(old)})
    for rel, pairs in IMPORT_FIXES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        report["import_fixes"] += [f"{rel}: {a} -> {b}" for a, b in pairs if a in text]
    report["root_fix"] = ROOT_FIX in (ROOT / "FastAPI/LangGraph/multi_persona/review_contract.py").read_text(encoding="utf-8")
    if execute:
        (ROOT / NEW_PKG).mkdir(parents=True, exist_ok=True)
        (ROOT / NEW_PKG / "__init__.py").write_text(INIT, encoding="utf-8")
        for move in report["moves"]:
            if move["tracked"]:
                subprocess.run(["git", "mv", "--", move["from"], move["to"]], cwd=ROOT, check=True)
            else:
                shutil.move(str(ROOT / move["from"]), str(ROOT / move["to"]))
            (ROOT / move["from"]).write_text(_shim(MOVES[move["from"]][1]), encoding="utf-8")
        contract = ROOT / NEW_PKG / "review_contract.py"
        contract.write_text(contract.read_text(encoding="utf-8").replace(ROOT_FIX, ROOT_NEW), encoding="utf-8")
        for rel, pairs in IMPORT_FIXES.items():
            path = ROOT / rel
            text = path.read_text(encoding="utf-8")
            for a, b in pairs:
                text = text.replace(a, b)
            path.write_text(text, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
