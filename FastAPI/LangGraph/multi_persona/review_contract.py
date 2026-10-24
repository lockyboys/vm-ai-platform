"""전체 소스 리뷰의 출력 계약. 모델 호출 없이 누락·문법 오류를 판정합니다."""
import ast
import re
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
    match = re.search(r"```python\r?\n(.*)\r?\n```", text, re.S)
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

def validate_review(text, query):
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
            named = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", diagnosis)) & old_functions.keys()
            if named and not any(
                name in new_functions and ast.dump(old_functions[name]) != ast.dump(new_functions[name])
                for name in named
            ):
                errors.append("진단된 함수 수정 미반영: " + ", ".join(sorted(named)))
    return errors
