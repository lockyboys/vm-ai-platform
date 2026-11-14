"""전체 소스 리뷰의 출력 계약. 모델 호출 없이 누락·문법 오류를 판정합니다."""
import ast
import importlib.machinery
import re
import sys
from pathlib import Path

HEADINGS = ("## 1. 전문가적 견해 및 종합 평가", "## 2. 위험도 및 진단 리포트", "## 3. 최종 수정 전체 소스 코드")

# 모듈 탐색 시 불필요한 중복 호출을 막고 튜플 조회를 위한 지원 확장자 모듈 수준 상수 캐시
_MODULE_SUFFIXES = tuple(importlib.machinery.all_suffixes())


def build_review_query(path, code, previous_error=""):
    """프롬프트 구분자만 줄바꿈하고 입력 소스의 escape는 보존합니다."""
    return (
        f"Python 소스 리뷰: {path}\n메모리·동시성·예외·리소스 해제를 확인하세요.\n"
        "LangChain/LangGraph가 있으면 설계 검토에 PROMPT_ENGINEER를 포함하세요.\n"
        + "\n".join(HEADINGS)
        + "\n세 제목을 순서대로 출력하고 3번에는 수정된 전체 소스를 닫힌 python 코드 블록으로 출력하세요.\n"
        "공개 함수·클래스와 기능을 보존하고 생략·플레이스홀더 없이 필요한 부분만 수정하세요.\n"
        "2번에서 수정이 필요하다고 지목한 함수는 3번에서 실행 코드까지 실제로 고치고 근거를 설명하세요. "
        "주석과 표현만 바꾼 코드는 수정으로 간주하지 않습니다. 수정 불필요한 진단은 명확히 구분하세요.\n"
        + (f"이전 실행 오류 로그(원인과 재현 조건을 분석해 수정안에 반영):\n{previous_error}\n" if previous_error else "")
        + "\n입력 소스:\n```python\n" + code + "\n```"
    )


def wants_full_source(query):
    return HEADINGS[2] in query


def source_block(text):
    """소스 문자열 안의 예시 fence를 위해 마지막 닫는 fence까지 읽습니다."""
    match = re.search(r"```python[ \t]*\r?\n(.*)\r?\n```[ \t]*", text, re.S)
    return match.group(1) if match else ""


def normalize_plan(plan, query, maximum):
    """필수 설계 담당과 최종 구현 담당이 상한 때문에 사라지지 않게 합니다."""
    if maximum < 1:
        raise ValueError("Persona budget must be positive")
    plan = list(dict.fromkeys(plan))
    required = ["PROMPT_ENGINEER"] if any(x in query.lower() for x in ("langchain", "langgraph")) else []
    if wants_full_source(query):
        if required and maximum < 2:
            raise ValueError("Full LangGraph review requires at least two personas")
        others = [p for p in plan if p not in required and p != "PARTNER"]
        return (required + others)[:maximum - 1] + ["PARTNER"]
    return (required + [p for p in plan if p not in required])[:maximum] or ["REVIEWER"]


# ---------------------------------------------------------------------------
# 2026-11-02 추가: import 대상 실존 검사 (LuckyBoys 승인)
# 사고 사례: LLM이 `-m harness.mcp.tools.multi_persona_tools`를 오타로 오판해 존재하지 않는
# `harness...`로 바꿨는데 ast.parse만 통과해 제안 소스가 "검증됨"으로 저장되었다.
# 원칙: 대상 소스·패키지를 import(실행)하지 않고 파일 시스템 경로만 확인한다.
# ---------------------------------------------------------------------------
# review_contract.py는 FastAPI/LangGraph/multi_persona/ 아래에 있으므로 parents[3]이 저장소 루트다.
# 단, 얕은 디렉터리 경로에서 실행되는 환경을 위해 길이를 안전하게 검사한다.
_parents = Path(__file__).resolve().parents
_DEFAULT_PROJECT_ROOT = _parents[3] if len(_parents) > 3 else _parents[-1]


def _module_references(tree):
    """소스가 참조하는 절대 모듈 이름을 모은다.

    - `import a.b` / `from a.b import c` (상대 import는 위치에 따라 달라지므로 제외)
    - 리스트·튜플 안의 `"-m", "a.b"` 문자열 쌍(서브프로세스로 띄우는 모듈 경로)
    """
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
        elif isinstance(node, (ast.List, ast.Tuple)):
            items = node.elts
            for first, second in zip(items, items[1:]):
                if (isinstance(first, ast.Constant) and first.value == "-m"
                        and isinstance(second, ast.Constant) and isinstance(second.value, str)):
                    names.add(second.value)
    return names


def _module_exists(name, roots):
    """모듈을 실행하지 않고 경로만으로 존재 여부를 판단한다.

    표준 라이브러리·내장 모듈은 최상위 이름만 확인한다(os.path처럼 파일이 없는 별칭이 있음).
    그 외에는 각 검색 루트에서 a/b/c.py, a/b/c/(패키지·네임스페이스), 확장 모듈(.so 등)을 찾는다.
    """
    parts = name.split(".")
    if not all(part.isidentifier() for part in parts):
        return False  # 모듈 이름으로 쓸 수 없는 문자열은 존재하지 않는 것으로 본다.
    top = parts[0]
    if top in sys.builtin_module_names or top in getattr(sys, "stdlib_module_names", ()):
        return True

    seen_roots = set()
    for root in roots:
        if not root:
            continue
        try:
            base = Path(root).resolve()
            if base in seen_roots or not base.is_dir():
                continue
            seen_roots.add(base)

            current_base = base
            for index, part in enumerate(parts):
                last = index == len(parts) - 1
                target_dir = current_base / part
                if last:
                    if target_dir.is_dir() or any((current_base / (part + s)).is_file() for s in _MODULE_SUFFIXES):
                        return True
                elif not target_dir.is_dir():
                    break  # 중간 패키지가 없으면 이 루트에서는 찾을 수 없다.
                current_base = target_dir
        except (OSError, RuntimeError, ValueError):
            # 권한 거부(PermissionError), 심볼릭 링크 루프(RuntimeError), 경로 형식 에러(ValueError) 건너뜀
            continue
    return False


def unresolved_imports(code_tree, original_tree, roots):
    """제안 소스에서 새로 깨진 import만 돌려준다.

    원본에서도 해석되지 않던 모듈(선택 의존성 등)은 제안 탓이 아니므로 제외한다.
    """
    original_missing = set()
    if original_tree is not None:
        original_missing = {n for n in _module_references(original_tree) if not _module_exists(n, roots)}
    return sorted(n for n in _module_references(code_tree)
                  if n not in original_missing and not _module_exists(n, roots))


def _strip_docstring_nodes(func_node):
    """함수 본문에서 첫 번째 구문인 docstring(Expr(Constant(str))) 노드를 제외한 실행 노드를 반환합니다."""
    body = func_node.body
    if body and isinstance(body[0], ast.Expr):
        val = getattr(body[0], "value", None)
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return body[1:]
    return body


def _is_executable_body_unchanged(old_fn, new_fn):
    """docstring 변경을 제외하고 두 함수의 실제 실행 AST가 동일한지 검사합니다."""
    old_stmts = [ast.dump(stmt) for stmt in _strip_docstring_nodes(old_fn)]
    new_stmts = [ast.dump(stmt) for stmt in _strip_docstring_nodes(new_fn)]
    return old_stmts == new_stmts


def validate_review(text, query, search_roots=None):
    """제목·문법·기존 최상위 심볼을 확인하며 모델의 내용 정확성까지 보증하지는 않습니다."""
    if not wants_full_source(query):
        return []
    errors = ["누락 제목: " + h for h in HEADINGS if h not in text]
    positions = [text.find(h) for h in HEADINGS]
    has_all_headings = all(position >= 0 for position in positions)
    if not errors and positions != sorted(positions):
        errors.append("제목 순서 오류")
    code = source_block(text[positions[2]:]) if (has_all_headings and positions[2] >= 0) else (
        source_block(text[text.find(HEADINGS[2]):]) if HEADINGS[2] in text else ""
    )
    if not code:
        return errors + ["닫힌 전체 Python 코드 블록 없음"]
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return errors + ["수정 소스 문법 오류: " + error.msg]
    if any(isinstance(n, ast.Constant) and n.value is Ellipsis for n in ast.walk(tree)):
        errors.append("생략 기호 Ellipsis 발견")
    original = source_block(query)
    try:
        old = ast.parse(original)
    except SyntaxError:
        old = None
    if old:
        kinds = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        missing = {n.name for n in old.body if isinstance(n, kinds)} - {n.name for n in tree.body if isinstance(n, kinds)}
        if missing:
            errors.append("기존 공개 심볼 누락: " + ", ".join(sorted(missing)))
        # 진단 표가 기존 함수를 수정 대상으로 지목했다면 실제 함수 본문 변화를 확인합니다.
        # 헤딩 순서가 올바르고 모두 존재하는 경우에만 안전하게 진단 영역을 슬라이스합니다.
        if has_all_headings and positions == sorted(positions):
            diagnosis = text[positions[1] + len(HEADINGS[1]):positions[2]]
            old_functions = {
                node.name: node for node in ast.walk(old)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            new_functions = {
                node.name: node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }

            # 라인 단위로 '수정 불필요', '수정불필요', '수정 불요' 등으로 판정된 심볼은 제외하고
            # 실제 수정 대상으로 지목된 함수 심볼만 추출합니다.
            target_names = set()
            no_fix_pattern = re.compile(r"수정\s*(?:불필요|불요|없음)|변경\s*불필요", re.IGNORECASE)
            for line in diagnosis.splitlines():
                line_funcs = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", line)) & old_functions.keys()
                if line_funcs and not no_fix_pattern.search(line):
                    target_names.update(line_funcs)

            # 지목된 함수 중 실제로 변경되지 않은 함수를 전수 검출합니다.
            # 주석 및 docstring만 변경된 편법 수정을 걸러내기 위해 docstring을 제거한 실행문 AST를 비교합니다.
            if target_names:
                unmodified = [
                    name for name in sorted(target_names)
                    if name not in new_functions or _is_executable_body_unchanged(old_functions[name], new_functions[name])
                ]
                if unmodified:
                    errors.append("진단된 함수 수정 미반영: " + ", ".join(unmodified))

    # 2026-11-02: 문법이 맞아도 존재하지 않는 모듈을 참조하면 실행 즉시 실패하므로 오류로 본다.
    # search_roots를 주지 않으면 저장소 루트 + 현재 sys.path에서 찾는다(테스트는 임시 루트를 넘김).
    roots = list(search_roots) if search_roots is not None else [_DEFAULT_PROJECT_ROOT, *sys.path]
    missing_modules = unresolved_imports(tree, old, roots)
    if missing_modules:
        errors.append("존재하지 않는 import 대상: " + ", ".join(missing_modules))
    return errors