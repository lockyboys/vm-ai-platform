검증관으로서 제공된 초안(PROMPT_ENGINEER, REVIEWER, BUG_HUNTER, PARTNER)의 분석 내용 및 수정안을 교차 검증하고, 검증 근거와 미확인 사항을 명시한 최종 리포트를 작성합니다.

---

### 초안 검증 및 교차 분석

1. **`source_block` 정규식 수정에 대한 검증 (BUG_HUNTER vs PARTNER)**
   - **BUG_HUNTER 주장**: `.*`를 `.*?`(비탐욕)로 바꾸어야 중간 코드 블록 추출 왜곡을 막을 수 있음.
   - **검증 결과 (기각)**: 원본 함수의 의도(`"""소스 문자열 안의 예시 fence를 위해 마지막 닫는 fence까지 읽습니다."""`)와 docstring 내에 마크다운 예시 펜스가 포함되는 케이스(예: 프롬프트 템플릿, 독스트링 코드 블록)를 고려하면 비탐욕(`.*?`) 사용 시 소스 내부의 첫 번째 닫는 펜스에서 파싱이 조기 종료되어 전체 소스가 잘리는 심각한 결함이 발생합니다.
   - **판정**: PARTNER의 분석대로 탐욕적 매칭을 유지하되, 마크다운 펜스 뒤 공백(trailing whitespace) 허용 패턴(`[ \t]*`)을 추가하는 방안이 타당합니다.

2. **`validate_review`의 지목 함수 검증 로직 검증 (REVIEWER & PARTNER)**
   - **초안 주장**: `not any(...)`는 지목된 함수 중 단 하나만 수정되어도 통과하는 결함이 있으므로 전수 검사(`unmodified`)로 변경해야 함.
   - **검증관 확인 결함 (오탐 위험 발견)**: 단순 전수 검사로 전환할 경우, 2번 진단 리포트에서 "수정 불필요"로 언급된 함수명까지 `named`에 포함되어 "진단된 함수 수정 미반영" 오류로 오탐(False Positive)되는 부작용이 발생합니다.
   - **판정 및 조치**: 진단 본문(`diagnosis`)에서 "수정 불필요", "수정불필요", "수정 불요" 등의 문맥에 포함된 심볼을 제외한 뒤, 실제 수정 대상으로 지목된 함수들에 대해 전수 검사하도록 필터링을 보강해야 합니다.

3. **`_DEFAULT_PROJECT_ROOT` 및 `_module_exists` I/O 예외 검증 (공통)**
   - **검증 결과 (인정)**: 파일 시스템 경로 깊이가 얕은 컨테이너/테스트 환경에서 `parents[3]`의 `IndexError` 발생 가능성과 권한 거부/깨진 심볼릭 링크 순회 시 `OSError` 미처리는 프로세스 중단을 유발할 수 있으므로 방어 코드가 반드시 필요합니다.

---

## 1. 전문가적 견해 및 종합 평가

본 모듈은 LLM을 사용한 코드 리뷰 파이프라인에서 결과물이 계약(Contract)을 준수했는지 비동기 호출 없이 순수 AST 파싱 및 파일 시스템 검증만으로 판정하는 결정론적 검증기입니다.

핵심 로직 검토 결과:
1. **함수 수정 판정의 논리 결함 및 오탐 취약성**: 기존 코드는 `not any(...)`로 인해 여러 함수가 지목되어도 1개만 수정되면 통과하는 허점이 있었습니다. 반면 초안들이 제안한 단순 전수 검사(`all` 또는 `unmodified`) 방식은 프롬프트 지침에 따라 작성된 "수정 불필요" 대상 함수까지 미수정 오류로 오인하는 치명적인 부작용이 있습니다. 라인 단위 문맥 필터링을 통해 "수정 불필요"로 진단된 심볼을 제외하고 실제 수정 요구 심볼만 전수 검사하도록 수정해야 합니다.
2. **파일 시스템 및 I/O 안전성 결여**: `_module_exists`에서 `sys.path`나 프로젝트 루트를 순회할 때 심볼릭 링크 순환, 권한 없는 디렉터리(`PermissionError`), 깨진 파일 경로 접근 시 예외 격리가 되어 있지 않아 전체 검증 프로세스가 크래시될 위험이 있습니다.
3. **경로 인덱싱 취약점**: 하드코딩된 `parents[3]`는 테스트 실행 환경이나 얕은 디렉터리 구조에서 `IndexError`를 발생시킵니다.

인터페이스 하위 호환성을 100% 유지하면서, 정규식의 엣지 케이스 및 파일 탐색 예외를 완벽히 차단하도록 개선했습니다.

---

## 2. 위험도 및 진단 리포트

| 대상 함수 / 심볼 | 위험도 | 진단 내용 및 근거 | 조치 방향 (수정 여부) |
| :--- | :--- | :--- | :--- |
| `validate_review` | **High** | 1. `not any(...)` 조건으로 인해 복수 함수 지목 시 1개만 수정되어도 검증을 통과함.<br>2. 단순 백틱 추출 시 진단 리포트의 '수정 불필요' 대상 함수까지 수정 누락으로 오탐됨. | **수정 필요**: 라인별 문맥에서 '수정 불필요/수정불필요' 제외 필터링 추가 및 수정 대상 함수 전수 검사(`unmodified`) 로직 적용. |
| `_module_exists` | **Medium** | 권한 없는 디렉터리 접근(`PermissionError`)이나 비정상적인 심볼릭 링크 경로 순회 시 `OSError`로 크래시 발생. 중복된 `roots`로 불필요한 I/O 발생. | **수정 필요**: `OSError` 예외 처리 보호 블록 추가 및 `seen_roots` 중복 제거. |
| `source_block` | **Medium** | 코드 펜스(` ```python ` 및 ` ``` `) 뒤에 공백(whitespace)이 포함된 경우 정규식 매칭 실패로 빈 문자열을 반환함. | **수정 필요**: 펜스 선언부 및 종료부 뒤 공백을 허용하도록 `[ \t]*` 정규식 보강. |
| `_DEFAULT_PROJECT_ROOT` | **Low** | 배포 위치나 테스트 환경에 따라 파일 경로의 깊이가 4단계 미만일 때 `IndexError` 발생 가능. | **수정 필요**: `parents`의 길이를 사전 검증하여 안전하게 fallback하도록 수정. |
| `build_review_query` | Info | 프롬프트 생성 함수로 문자열 조합 정상 작동. | **수정 불필요** |
| `wants_full_source` | Info | 상수 포함 여부 판별 정상 작동. | **수정 불필요** |
| `normalize_plan` | Info | 페르소나 제약 조건 정규화 정상 작동. | **수정 불필요** |
| `_module_references` | Info | AST 기반 모듈 참조 추출 정상 작동. | **수정 불필요** |
| `unresolved_imports` | Info | 원본 AST 대비 신규 누락 모듈 차집합 연산 정상 작동. | **수정 불필요** |

### 미확인 사항 및 가정
- 진단 리포트의 자연어 표현 중 "수정 불필요", "수정불필요", "수정 불요", "변경 불필요", "수정 없음" 외의 특이한 부정 표현이 사용될 경우 오탐 필터링에서 누락될 수 있으므로 일반적인 패턴을 포괄하도록 정규식을 구성했습니다.

---

## 3. 최종 수정 전체 소스 코드

```python
"""전체 소스 리뷰의 출력 계약. 모델 호출 없이 누락·문법 오류를 판정합니다."""
import ast
import importlib.machinery
import re
import sys
from pathlib import Path

HEADINGS = ("## 1. 전문가적 견해 및 종합 평가", "## 2. 위험도 및 진단 리포트", "## 3. 최종 수정 전체 소스 코드")


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

    suffixes = importlib.machinery.all_suffixes()  # .py, .pyc, .cpython-*.so 등
    seen_roots = set()
    for root in roots:
        try:
            base = Path(root).resolve()
            if base in seen_roots or not base.is_dir():
                continue
            seen_roots.add(base)

            for index, part in enumerate(parts):
                last = index == len(parts) - 1
                target_dir = base / part
                if last:
                    if target_dir.is_dir() or any((base / (part + s)).is_file() for s in suffixes):
                        return True
                elif not target_dir.is_dir():
                    break  # 중간 패키지가 없으면 이 루트에서는 찾을 수 없다.
                base = target_dir
        except OSError:
            # 권한 거부(PermissionError), 깨진 링크 순환 등 I/O 실패 시 안전하게 건너뜀
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


def validate_review(text, query, search_roots=None):
    """제목·문법·기존 최상위 심볼을 확인하며 모델의 내용 정확성까지 보증하지는 않습니다."""
    if not wants_full_source(query):
        return []
    errors = ["누락 제목: " + h for h in HEADINGS if h not in text]
    positions = [text.find(h) for h in HEADINGS]
    if not errors and positions != sorted(positions):
        errors.append("제목 순서 오류")
    code = source_block(text[text.find(HEADINGS[2]):]) if HEADINGS[2] in text else ""
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
        if all(position >= 0 for position in positions):
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
            if target_names:
                unmodified = [
                    name for name in sorted(target_names)
                    if name not in new_functions or ast.dump(old_functions[name]) == ast.dump(new_functions[name])
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
```