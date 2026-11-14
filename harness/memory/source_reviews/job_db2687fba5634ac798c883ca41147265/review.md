### [검증관 평가 및 초안 검증]
- **초안 검증 결과**: 초안의 다중 페르소나(PROMPT_ENGINEER, REVIEWER, BUG_HUNTER, PARTNER) 중 PROMPT_ENGINEER는 디렉터리 경로명(`FastAPI/LangGraph`)에 반응하여 실제 구현을 회피하려 했으나, 본 코드는 순수 테트리스 비즈니스 로직이므로 코드 레벨의 수정이 필수적입니다. REVIEWER, BUG_HUNTER, PARTNER가 도출한 결함 원인(`rotate`의 전치 미완성, `clear_lines`의 상단 패딩 누락) 및 해결 방식(`zip(*piece[::-1])`, `[[0] * cols for _ in range(cleared)] + kept`)은 정확합니다.
- **수정 근거**:
  1. `rotate`: 2차원 리스트의 시계 방향 90도 회전은 전치($A^T$) 후 좌우 반전이거나, 상하 반전 후 전치여야 합니다. 기존의 `zip(*piece)`는 대각선 대칭(전치)만 수행하므로 `zip(*piece[::-1])`으로 올바른 회전을 완성합니다.
  2. `clear_lines`: 줄 삭제 후 보드 높이(`len(board)`)가 줄어드는 치명적 불변식 훼손을 해결하기 위해 삭제된 개수(`cleared`)만큼 상단에 `[0] * cols` 빈 행을 채웁니다.
  3. `can_place`, `clear_lines`: 빈 보드(`[]` 또는 `[[]]`)가 입력될 때 `board[0]` 인덱싱 오류(`IndexError`)를 방지하는 방어 코드를 추가합니다.
- **미확인 사항**: 각 행의 열 길이가 불균일한 비정형(jagged) 2차원 리스트 입력 가능성은 테트리스 도메인 규칙상 `new_board` 규격($N \times M$)을 준수한다고 가정하고 별도의 톱니형 행렬 보정은 포함하지 않았습니다.

---

## 1. 전문가적 견해 및 종합 평가
제공된 `tetris_core.py` 모듈은 전역 가변 상태나 외부 I/O 핸들을 보유하지 않아 메모리 누수 및 동시성 레이스 컨디션의 위험이 없습니다. `place` 및 `clear_lines`는 기존 보드를 직접 변이(mutate)하지 않고 얕은 복사(`[row[:] for row in board]`)를 기반으로 새로운 보드를 반환하여 함수형 불변성을 잘 유지하고 있습니다.

그러나 핵심 알고리즘 두 곳에 명백한 논리 결함이 존재합니다:
1. `rotate`는 수학적 전치(Transpose)만 수행하여 블록이 대각선으로 반전될 뿐 시계 방향 회전이 동작하지 않습니다.
2. `clear_lines`는 완성된 행을 걸러낸 뒤 상단에 빈 행을 보충하지 않아, 블록을 소거할 때마다 전체 게임 보드의 높이가 영구적으로 줄어들고 이후 충돌 판정 범위를 파괴합니다.

이 두 결함을 완전히 수정하고, 빈 리스트 입력 시 발생할 수 있는 `IndexError` 예외 방어를 보강하여 상태 불변성을 확립했습니다.

---

## 2. 위험도 및 진단 리포트

| 대상 함수 | 위험도 | 진단 결과 및 결함 내용 | 조치 내용 및 수정 근거 | 수정 필요 여부 |
| :--- | :--- | :--- | :--- | :--- |
| `rotate` | **높음 (Critical)** | `zip(*piece)`는 단순 전치($A^T$)에 불과하여 90도 시계 방향 회전이 아닌 주대각선 대칭을 수행함. | 행 순서를 뒤집은 뒤 전치(`zip(*piece[::-1])`)하여 시계 방향 90도 회전 완성. | **수정 필요** |
| `clear_lines` | **높음 (Critical)** | 완성된 줄을 제외한 `kept`만 반환하여 라인 소거 시 보드 전체 행 수(`rows`)가 줄어드는 불변식 위반 발생. | `cleared` 개수만큼 상단에 `[[0] * cols for _ in range(cleared)]`를 생성하여 `kept` 앞에 결합. | **수정 필요** |
| `can_place` | **중간 (Medium)** | `board`가 빈 리스트(`[]`)로 전달될 경우 `len(board[0])` 접근 시 `IndexError` 발생 위험. | 함수 진입부에서 빈 보드 여부를 검증하여 `False` 반환하도록 방어 코드 추가. | **수정 필요** |
| `new_board` | 낮음 (Low) | 행/열 수 음수 입력 방어(`ValueError`)가 구현되어 있고 리스트 컴프리헨션으로 독립 참조를 보장함. | 현행 유지. | 수정 불필요 |
| `place` | 낮음 (Low) | 원본 보드를 복사(`[row[:] ...]`)하여 변경하므로 불변성이 보장되며 사전 `can_place` 검증 수행. | 현행 유지. | 수정 불필요 |

---

## 3. 최종 수정 전체 소스 코드

```python
"""스스로 고치는 리뷰 앱 시연용 테트리스 핵심 로직(화면 없음) (2026-11-10).

보드는 rows x cols 리스트(0=빈칸, 1=블록). 화면·입력 처리는 넣지 않아 테스트만으로 검증할 수 있다.
테스트: harness/tests/test_selffix_demo_tetris_20261110.py
"""


def new_board(rows: int = 20, cols: int = 10) -> list[list[int]]:
    """빈 보드를 만든다."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    return [[0] * cols for _ in range(rows)]


def rotate(piece: list[list[int]]) -> list[list[int]]:
    """조각을 시계 방향으로 90도 돌린다."""
    if not piece or not piece[0]:
        return []
    # 단순 전치(zip(*piece)) 대신 상하를 뒤집은 뒤 전치하여 90도 시계 방향 회전을 완성한다.
    return [list(row) for row in zip(*piece[::-1])]


def can_place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> bool:
    """조각이 보드 안에 있고 기존 블록과 겹치지 않으면 True."""
    if not board or not board[0]:
        return False
    board_rows = len(board)
    board_cols = len(board[0])
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if not cell:
                continue
            y, x = top + r, left + c
            if y < 0 or y >= board_rows or x < 0 or x >= board_cols or board[y][x]:
                return False
    return True


def place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> list[list[int]]:
    """조각을 놓은 새 보드를 돌려준다(원래 보드는 바꾸지 않는다). 놓을 수 없으면 ValueError."""
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed here")
    result = [row[:] for row in board]
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if cell:
                result[top + r][left + c] = 1
    return result


def clear_lines(board: list[list[int]]) -> tuple[list[list[int]], int]:
    """가득 찬 줄을 지우고 위에 빈 줄을 채운 (새 보드, 지운 줄 수)를 돌려준다."""
    if not board or not board[0]:
        return [], 0
    cols = len(board[0])
    kept = [row[:] for row in board if not all(row)]
    cleared = len(board) - len(kept)
    # 지운 줄(cleared)만큼 상단에 0으로 채워진 빈 줄을 추가해 원래 보드 행 높이를 유지한다.
    empty_lines = [[0] * cols for _ in range(cleared)]
    return empty_lines + kept, cleared
```