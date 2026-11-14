## 1. 전문가적 견해 및 종합 평가

- **프레임워크 및 환경 검토**: 본 엔진은 LangChain/LangGraph 등 외부 LLM 오케스트레이션 프레임워크나 외부 I/O가 없는 순수 결정론적 파이썬 인메모리 테트리스 규칙 엔진입니다. 프롬프트 인젝션, 비결정론적 출력 편차, 외부 API 호출 지연 위험은 없습니다.
- **실패 원인 및 검증 분석**: 직전 테스트에서 발생한 단일 실패(`test_case[c182]: AssertionError: m.text_to_board('#.\n') -> ('ok', [[1, 0]]), 기대 ('raises', 'ValueError')`)의 근본 원인은 `str.splitlines()`의 동작 특성에 있습니다. `splitlines()`는 표준 규격상 문자열 끝에 위치한 단일 개행 문자(`\n`)를 분리 행으로 보존하지 않고 생략하므로, 끝 개행이 포함된 비정형 텍스트를 1행 보드로 잘못 파싱했습니다.
- **아키텍처 및 자원 관리 평가**:
  - **메모리 및 불변성**: `copy_board` 및 2차원 리스트 복사(슬라이싱)를 통해 입력 보드와 조각의 불변성을 유지하고 있으며, 순환 참조나 메모리 누수 요인이 없습니다.
  - **동시성 및 상태 격리**: `GameState`는 인스턴스 단위로 멤버 변수를 격리하고 전역 가변 상태를 참조/변조하지 않으므로 스레드 안전성(참조 격리)이 확보되어 있습니다.
  - **예외 처리 완전성**: `splitlines()`를 `split('\n')`으로 전환하여 끝 개행이 후속 빈 문자열 행(`''`)으로 남아 행 길이 불일치(`ragged board text`)로 정확히 `ValueError`를 발생시키도록 보완했습니다.

---

## 2. 위험도 및 진단 리포트

### [수정 대상]
- **`text_to_board(text)` (위험도: High — 테스트 실패 직접 유발)**
  - **진단 및 재현 조건**: `text_to_board('#.\n')` 호출 시 `lines = text.splitlines()`를 거치면 끝 개행이 무시되어 `lines`가 `['#.']` 1개 행만으로 구성됩니다. 이로 인해 빈 줄 검증 및 불균형 검증을 우회하여 `[[1, 0]]`을 정상 반환합니다.
  - **수정 근거**: `board_to_text`는 `\n.join(...)`으로 직렬화하므로 끝에 후행 개행을 붙이지 않습니다. 따라서 올바른 역직렬화(bijective mapping) 검증을 위해서는 `text.split('\n')`을 사용해야 끝 개행 발생 시 `['#.', '']`로 분리되어 두 번째 행의 길이가 첫 행의 너비와 불일치하게 되고, 의도된 대로 `ValueError("ragged board text")`가 발생합니다.

### [수정 불필요 대상 (진단 통과 및 유지)]
- **`new_board(rows, cols)` (위험도: Low)**: `isinstance(..., bool)` 검사를 선행하여 파이썬의 `bool`이 `int`의 서브클래스로 통과하는 취약점을 방어하고 있습니다.
- **`place`, `clear_lines`, `drop_row`, `hard_drop` (위험도: Low)**: 원본 보드를 변형하지 않고 `copy_board`를 통해 신규 객체를 반환하는 계약을 정확히 준수하고 있습니다.
- **`score_for_lines`, `level_for_lines`, `GameState` (위험도: Low)**: 타입 검증, 음수 예외, 레벨 반영 전 점수 계산, 중복 홀드 방지(`already held this turn`) 로직이 명세와 일치합니다.

---

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트. top은 행, left는 열(0부터).
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않고 새 객체를 돌려준다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import random

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
    lines = text.split("\n")
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
    return [y for y, row in enumerate(board) if all(row)]


def clear_lines(board):
    """가득 찬 행을 지우고 위에 빈 행을 채운 (새 보드, 지운 행 수). 높이·너비는 그대로."""
    cols = len(board[0]) if board else 0
    kept = [row[:] for row in board if not all(row)]
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
    return max(1, 48 - 5 * level)


def combo_bonus(combo, level):
    """연속으로 줄을 지운 횟수 combo(1부터)의 보너스 = 50 * combo * (level + 1). combo가 0 이하면 0."""
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
        return self.start_level + level_for_lines(self.lines)

    def record_clear(self, cleared):
        """조각 하나를 놓은 뒤 지운 줄 수를 반영한다. 점수는 반영 전 레벨로 계산한다.
        지웠으면 combo += 1 후 줄 점수 + 콤보 보너스(2번째 연속부터, combo-1 기준), 못 지웠으면 combo = 0.
        놓을 때마다 다시 보관할 수 있게 된다. 반환: 이번에 얻은 점수."""
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
        if not self.can_hold:
            raise ValueError("already held this turn")
        previous, self.held = self.held, current
        self.can_hold = False
        return previous
```