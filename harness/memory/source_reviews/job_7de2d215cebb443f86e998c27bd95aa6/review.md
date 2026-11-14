## 1. 전문가적 견해 및 종합 평가

### 초안 검증 및 종합 평가
1. **역할 위반 및 포맷 오류 시정**:
   - 초안은 내부에 `### PROMPT_ENGINEER`와 `### PARTNER`라는 임의의 가상 역할 헤더를 생성하고, 코드를 이관한다는 명목의 메타 텍스트를 포함하고 있었습니다.
   - 본 검증에서는 지침에 명시된 3단계 섹션(`## 1. 전문가적 견해 및 종합 평가`, `## 2. 위험도 및 진단 리포트`, `## 3. 최종 수정 전체 소스 코드`) 규격을 엄격히 준수하도록 재구성하였습니다.
2. **LangChain / LangGraph 포함 여부 검증**:
   - 지침상 "LangChain/LangGraph가 있으면 설계 검토에 PROMPT_ENGINEER를 포함하라"고 명시되어 있으나, 대상 파일은 순수 테트리스 엔진 구현체이며 LLM 관련 라이브러리 및 호출부가 전혀 없습니다. 따라서 인위적인 프롬프트 엔지니어링 분기는 배제하고 본질적인 엔진 로직 결함 검증에 집중합니다.
3. **핵심 결함 분석 및 수정의 타당성**:
   - **`full_rows` / `clear_lines` Vacuous Truth 방어**: `all([])`이 `True`를 반환하는 파이썬 특성상, 유효하지 않은 빈 행(`[]`)이 유입될 때 가득 찬 행으로 오인하여 행이 소실되는 결함이 존재합니다. `row and all(row)` 조건으로 보강하는 조치는 필수적입니다.
   - **검증 일관성 결여 방어**: `gravity_frames`와 `combo_bonus`에서 `level` 인자의 음수 및 bool 타입 검증이 누락되어 있었습니다. 음수 레벨 입력 시 비정상 프레임 수(>48)나 음수 보너스가 산출되는 결함이 있어, 타 함수들과 동일한 수준(`not isinstance(level, int) or isinstance(level, bool) or level < 0`)의 방어 코드를 적용합니다.
   - **동시성(Concurrency) 안전성**: FastAPI나 비동기 워커 환경에서 인스턴스 참조가 공유될 경우 점수/홀드 상태 오염이 발생할 수 있으므로 `threading.RLock` 기반의 동기화를 반영합니다.
   - **근거 및 미확인 사항**:
     - *근거*: Python 언어 스펙(`all([]) is True`), 기존 함수(`new_board`, `score_for_lines`)의 타입 검사 컨벤션 일치.
     - *미확인 사항*: 외부 하네스 테스트(`bench` 파일)가 `GameState.log`의 타입을 순수 `list`로 전제하는지 여부. 초안 중 일부의 `deque` 교체 제안은 기존 리스트 메서드(`pop`, 슬라이싱 등)와의 호환성을 깨뜨릴 위험이 있으므로 공개 속성 호환성을 위해 `list` 인터페이스를 그대로 유지합니다.

---

## 2. 위험도 및 진단 리포트

| 번호 | 함수 / 클래스 | 위험도 | 문제점 및 진단 내용 | 조치 및 수정 근거 (수정 여부) |
|---|---|---|---|---|
| 1 | `full_rows`, `clear_lines` | **High** | 빈 행(`[]`)이 포함된 보드 입력 시 `all([])`이 `True`로 평가되어 빈 줄을 가득 찬 줄로 오판정하고 삭제함. | **수정 필요**: `all(row)`를 `bool(row) and all(row)`로 수정하여 빈 리스트 행에 대한 Vacuous truth 오동작 방지. |
| 2 | `gravity_frames` | **Medium** | `level`에 대한 타입/음수 검증이 없어 음수나 bool 값이 전달될 경우 48 이상의 비정상 프레임 계산. | **수정 필요**: `level` 타입(`isinstance(..., int) and not isinstance(..., bool)`) 및 음수 검증을 추가하여 위반 시 `ValueError` 발생하도록 수정. |
| 3 | `combo_bonus` | **Medium** | `level`에 대한 정수 및 음수 검증이 누락되어 음수 레벨 전달 시 음수 보너스가 반환될 수 있음. | **수정 필요**: `level` 유효성 검증(정수, bool 배제, 0 이상)을 추가하고 위반 시 `ValueError` 발생. |
| 4 | `GameState` | **Medium** | 멀티스레드 환경에서 `record_clear`, `hold`, `level` 속성 호출 시 경쟁 상태(Race Condition) 발생 위험. | **수정 필요**: `threading.RLock`을 추가하여 상태 조회 및 갱신을 원자적으로 처리. |
| 5 | `text_to_board` 등 보드 처리부 | **Low** | 입력 유효성 및 경계 처리가 docstring 명세대로 충실히 방어되어 있음. | **수정 불필요**: 명세에 부합하므로 기존 로직 유지. |
| 6 | LLM / Graph 파이프라인 | **N/A** | LangChain / LangGraph 컴포넌트 부재. | **수정 불필요**: 순수 로직 파일이므로 프롬프트 엔지니어링 미적용. |

---

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트. top은 행, left는 열(0부터).
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않고 새 객체를 돌려준다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import random
import threading

# 표준 테트로미노 모양(#=블록, .=빈칸, 위 행부터):
#   I: ####   O: ##/##   T: ###/.#.   S: .##/##.   Z: ##./.##   J: #../###   L: ..#/###
PIECES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[1, 1, 1], [0, 1, 0]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}
# 한 번에 지운 줄 수(0~4줄)별 기본 점수: 0, 40, 100, 300, 1200점(NES 방식).
LINE_SCORES = [0, 40, 100, 300, 1200]
LINES_PER_LEVEL = 10


# ---------------------------------------------------------------- 보드
def new_board(rows=20, cols=10):
    """빈 보드. rows·cols는 1 이상 정수, 아니면 ValueError."""
    if (
        not isinstance(rows, int)
        or not isinstance(cols, int)
        or isinstance(rows, bool)
        or isinstance(cols, bool)
        or rows < 1
        or cols < 1
    ):
        raise ValueError("rows and cols must be positive integers")
    return [[0] * cols for _ in range(rows)]


def copy_board(board):
    """행까지 새로 만든 복사본."""
    return [row[:] for row in board]


def board_to_text(board):
    """블록은 '#', 빈칸은 '.'으로 위 행부터 한 줄씩, 줄 사이는 '\\n'."""
    return "\n".join("".join("#" if cell else "." for cell in row) for row in board)


def text_to_board(text):
    """board_to_text의 역변환(첫 줄이 맨 위 행, 칸은 int 0/1). 빈 문자열, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError."""
    if not text:
        raise ValueError("empty text")
    lines = text.splitlines()
    if not lines:
        raise ValueError("empty text")
    width = len(lines[0])
    if width == 0:
        raise ValueError("ragged board text")
    board = []
    for line in lines:
        if len(line) != width:
            raise ValueError("ragged board text")
        row = []
        for ch in line:
            if ch == "#":
                row.append(1)
            elif ch == ".":
                row.append(0)
            else:
                raise ValueError(f"invalid character in board text: {ch}")
        board.append(row)
    return board


# ---------------------------------------------------------------- 조각
def rotate_cw(piece):
    """시계 방향 90도: 위쪽 행이 오른쪽 열이 된다."""
    return [list(row) for row in zip(*piece[::-1])]


def rotate_ccw(piece):
    """반시계 방향 90도: 위쪽 행이 왼쪽 열이 된다(뒤집힌 순서)."""
    return [list(row) for row in zip(*piece)][::-1]


def rotate_180(piece):
    """180도: 행 순서와 각 행의 칸 순서를 모두 뒤집는다."""
    return [row[::-1] for row in piece[::-1]]


def piece_cells(piece):
    """블록 칸의 (행, 열) 목록(행 우선, 왼쪽부터)."""
    return [(r, c) for r, row in enumerate(piece) for c, cell in enumerate(row) if cell]


def trim_piece(piece):
    """바깥쪽의 빈 행·빈 열을 잘라낸다. 블록이 하나도 없으면 ValueError."""
    cells = piece_cells(piece)
    if not cells:
        raise ValueError("piece has no blocks")
    top = min(r for r, _ in cells)
    bottom = max(r for r, _ in cells)
    left = min(c for _, c in cells)
    right = max(c for _, c in cells)
    return [row[left : right + 1] for row in piece[top : bottom + 1]]


def piece_size(piece):
    """(높이, 너비)."""
    if not piece:
        return 0, 0
    return len(piece), len(piece[0])


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True(빈칸은 밖에 있어도 된다)."""
    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0
    for r, c in piece_cells(piece):
        y, x = top + r, left + c
        if y < 0 or y >= rows or x < 0 or x >= cols:
            return False
        if board[y][x]:
            return False
    return True


def place(board, piece, top, left):
    """조각을 놓은 새 보드. 놓을 수 없으면 ValueError. 조각의 빈칸은 기존 블록을 지우지 않는다."""
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed here")
    result = copy_board(board)
    for r, c in piece_cells(piece):
        result[top + r][left + c] = 1
    return result


def full_rows(board):
    """가득 찬 행 번호 목록(오름차순)."""
    return [y for y, row in enumerate(board) if row and all(row)]


def clear_lines(board):
    """가득 찬 행을 지우고 위에 빈 행을 채운 (새 보드, 지운 행 수). 높이·너비는 그대로."""
    cols = len(board[0]) if board else 0
    kept = [row[:] for row in board if not (row and all(row))]
    cleared = len(board) - len(kept)
    return [[0] * cols for _ in range(cleared)] + kept, cleared


def drop_row(board, piece, left, top=0):
    """top(기본 0 = 맨 위 행)에서 아래로 떨어뜨렸을 때 멈추는 행. 시작 위치에 놓을 수 없으면 ValueError."""
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot start here")
    while can_place(board, piece, top + 1, left):
        top += 1
    return top


def hard_drop(board, piece, left, top=0):
    """top(기본 0)에서 끝까지 떨어뜨려 놓은 뒤 줄을 지운 튜플 (새 보드, 떨어진 칸 수, 지운 행 수)."""
    landing = drop_row(board, piece, left, top)
    placed = place(board, piece, landing, left)
    cleared_board, cleared = clear_lines(placed)
    return cleared_board, landing - top, cleared


def shift(board, piece, top, left, dx):
    """좌우로 dx칸 옮길 수 있으면 새 left, 막히면 원래 left(한 번에 dx칸, 중간 칸은 보지 않는다)."""
    if can_place(board, piece, top, left + dx):
        return left + dx
    return left


def wall_kick(board, piece, top, left, offsets=((0, 0), (0, -1), (0, 1), (-1, 0))):
    """offsets(행, 열 이동)를 순서대로 시도해 처음 놓을 수 있는 (top, left). 모두 막히면 None.

    기본 시도 순서: 제자리 (0, 0) → 왼쪽 (0, -1) → 오른쪽 (0, 1) → 위 (-1, 0).
    """
    for dr, dc in offsets:
        if can_place(board, piece, top + dr, left + dc):
            return top + dr, left + dc
    return None


def is_game_over(board, piece, left):
    """맨 위(top=0)에 조각을 놓을 수 없으면 True."""
    return not can_place(board, piece, 0, left)


# ---------------------------------------------------------------- 보드 분석
def column_heights(board):
    """열마다 맨 위 블록부터 바닥까지의 높이(블록이 없으면 0)."""
    if not board or not board[0]:
        return []
    rows = len(board)
    cols = len(board[0])
    heights = []
    for x in range(cols):
        h = 0
        for y in range(rows):
            if board[y][x]:
                h = rows - y
                break
        heights.append(h)
    return heights


def aggregate_height(board):
    """열 높이의 합."""
    return sum(column_heights(board))


def max_height(board):
    """가장 높은 열의 높이."""
    heights = column_heights(board)
    return max(heights) if heights else 0


def count_holes(board):
    """구멍 수: 어떤 열에서 블록 아래에 있는 빈칸."""
    if not board or not board[0]:
        return 0
    holes = 0
    cols = len(board[0])
    rows = len(board)
    for x in range(cols):
        seen_block = False
        for y in range(rows):
            if board[y][x]:
                seen_block = True
            elif seen_block:
                holes += 1
    return holes


def bumpiness(board):
    """이웃한 열 높이 차이의 절댓값 합."""
    heights = column_heights(board)
    if len(heights) <= 1:
        return 0
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).
    cleared가 0~4가 아니거나 level이 음수면 ValueError."""
    if (
        not isinstance(cleared, int)
        or isinstance(cleared, bool)
        or cleared < 0
        or cleared > 4
    ):
        raise ValueError("cleared must be between 0 and 4")
    if not isinstance(level, int) or isinstance(level, bool) or level < 0:
        raise ValueError("level must not be negative")
    return LINE_SCORES[cleared] * (level + 1)


def level_for_lines(total_lines):
    """누적 줄 수로 레벨(10줄마다 1). 음수면 ValueError."""
    if (
        not isinstance(total_lines, int)
        or isinstance(total_lines, bool)
        or total_lines < 0
    ):
        raise ValueError("total_lines must not be negative")
    return total_lines // LINES_PER_LEVEL


def lines_to_next_level(total_lines):
    """다음 레벨까지 남은 줄 수(1~10)."""
    if (
        not isinstance(total_lines, int)
        or isinstance(total_lines, bool)
        or total_lines < 0
    ):
        raise ValueError("total_lines must not be negative")
    return LINES_PER_LEVEL - (total_lines % LINES_PER_LEVEL)


def gravity_frames(level):
    """한 칸 떨어지는 데 걸리는 프레임: 48 - 5*level, 최소 1."""
    if not isinstance(level, int) or isinstance(level, bool) or level < 0:
        raise ValueError("level must not be negative")
    return max(1, 48 - 5 * level)


def combo_bonus(combo, level):
    """연속으로 줄을 지운 횟수 combo(1부터)의 보너스 = 50 * combo * (level + 1). combo가 0 이하면 0."""
    if not isinstance(level, int) or isinstance(level, bool) or level < 0:
        raise ValueError("level must not be negative")
    if combo <= 0:
        return 0
    return 50 * combo * (level + 1)


def bag_sequence(count, seed):
    """7-bag 순서: 조각 이름('I','O','T','S','Z','J','L' 문자열) 7종을 이름순으로 한 묶음씩 random.Random(seed)로 섞어
    이어 붙인 앞 count개(seed가 같으면 같은 순서). count < 0이면 ValueError."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must not be negative")
    rng = random.Random(seed)
    sequence = []
    while len(sequence) < count:
        bag = sorted(PIECES.keys())
        rng.shuffle(bag)
        sequence.extend(bag)
    return sequence[:count]


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다. 인스턴스마다 상태를 따로 가진다."""

    def __init__(self, level=0):
        # 초기 상태: 점수·줄 수·콤보 0, 시작 레벨 = level, 보관 조각 없음(None), 보관 가능, 기록은 빈 목록.
        if not isinstance(level, int) or isinstance(level, bool) or level < 0:
            raise ValueError("level must not be negative")
        self._lock = threading.RLock()
        self.score = 0
        self.lines = 0
        self.start_level = level
        self.combo = 0
        self.held = None
        self.can_hold = True
        self.log = []

    @property
    def level(self):
        """시작 레벨 + 누적 줄로 오른 레벨."""
        with self._lock:
            return self.start_level + level_for_lines(self.lines)

    def record_clear(self, cleared):
        """조각 하나를 놓은 뒤 지운 줄 수를 반영한다. 점수는 반영 전 레벨로 계산한다.
        지웠으면 combo += 1 후 줄 점수 + 콤보 보너스(2번째 연속부터, combo-1 기준), 못 지웠으면 combo = 0.
        놓을 때마다 다시 보관할 수 있게 된다. 반환: 이번에 얻은 점수."""
        with self._lock:
            current_level = self.level
            gained = score_for_lines(cleared, current_level)
            if cleared:
                self.combo += 1
                gained += combo_bonus(self.combo - 1, current_level)
            else:
                self.combo = 0
            self.lines += cleared
            self.score += gained
            self.can_hold = True
            self.log.append((cleared, gained))
            return gained

    def hold(self, current):
        """현재 조각 이름을 보관하고 이전 보관 조각(없으면 None)을 돌려준다.
        한 번 놓기 전에 두 번 보관하면 ValueError."""
        with self._lock:
            if not self.can_hold:
                raise ValueError("already held this turn")
            previous, self.held = self.held, current
            self.can_hold = False
            return previous
```