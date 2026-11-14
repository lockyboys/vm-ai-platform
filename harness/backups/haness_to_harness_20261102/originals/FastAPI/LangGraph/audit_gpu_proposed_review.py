"""GPU 원본과 제안 소스의 AST 구조·크기·문법을 읽기 전용으로 비교합니다."""
import json
import shlex
import subprocess
import sys
import config
from haness.mcp.tools.ssh_execution_tools import run_remote

plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py",
                  ssh_target="gpu")
script = r'''
import ast, difflib, hashlib, json
from pathlib import Path
base = Path("/data/vm_project/FastAPI/LangGraph/multi_persona")
source = base / "multi_persona_agent_gemini.py"
proposed = base / "multi_persona_agent_gemini.proposed.py"
report = base / "multi_persona_agent_gemini.review.md"
original = source.read_text(encoding="utf-8")
changed = proposed.read_text(encoding="utf-8")
old_tree, new_tree = ast.parse(original), ast.parse(changed)
def names(tree):
    result = set()
    def visit(nodes, prefix=""):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                result.add(name)
                visit(node.body, name + ".")
    visit(tree.body)
    return result
old, new = names(old_tree), names(new_tree)
old_lines, new_lines = original.splitlines(), changed.splitlines()
matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
print(json.dumps({
    "original_chars":len(original),"proposed_chars":len(changed),
    "original_lines":len(old_lines),"proposed_lines":len(new_lines),
    "original_defs":len(old),"proposed_defs":len(new),
    "missing_defs":sorted(old-new)[:80],"missing_count":len(old-new),
    "added_defs":sorted(new-old)[:80],"added_count":len(new-old),
    "matching_lines":sum(block.size for block in matcher.get_matching_blocks()),
    "syntax":"OK","proposed_sha256":hashlib.sha256(proposed.read_bytes()).hexdigest(),
    "diff":"\n".join(difflib.unified_diff(old_lines,new_lines,fromfile="original",tofile="proposed",
                                    n=2))[:12000],
    "review_head":report.read_text(encoding="utf-8").split("## 3. 최종 수정 전체 소스 코드",1)[0][:6000]
},ensure_ascii=False))
'''
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script])]
result = subprocess.run(command, capture_output=True, text=True, timeout=60)
print(result.stdout, end="")
print(result.stderr, file=sys.stderr, end="")
raise SystemExit(result.returncode)
