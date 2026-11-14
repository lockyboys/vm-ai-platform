## 1. 전문가적 견해 및 종합 평가

초안의 PARTNER 코드는 주요 오류를 수정했지만, `T`와 `J`의 초기 모양이 동일한 문제는 남아 있습니다. 아래 코드에서는 이를 추가로 수정했습니다. `bag_sequence`는 기존 소스의 반환 형식인 **조각 행렬 목록**을 유지합니다.

제공된 소스의 정적 검토 결과이며, 실제 파일·호출자·테스트 실행 결과는 확인하지 못했습니다. 입력 코드에 LangChain/LangGraph 사용은 없어 PROMPT_ENGINEER 설계 검토 대상은 아닙니다.

## 2. 위험도 및 진단 리포트

- **높음 — 공유 참조:** `new_board`, `copy_board`, `place`, `clear_lines`, `bag_sequence`, `GameState.__init__`의 행·조각·기본 로그 공유를 수정했습니다. 명시적으로 전달한 `log`는 호출자와 공유합니다.
- **높음 — 배치와 상태:** `can_place`, `place`, `drop_row`, `hard_drop`, `shift`, `wall_kick`, `is_game_over`, `GameState`의 초기화·레벨·갱신·보관을 수정했습니다. 빈 조각 낙하는 무한 반복을 막기 위해 거부합니다. 동일 `GameState`의 동시 접근은 **호출자 동기화가 필요**합니다.
- **높음 — 조각과 보드:** 중복된 `T`·`Z`·`L` 모양 및 `rotate_cw`, `rotate_ccw`, `rotate_180`, `piece_cells`, `trim_piece`, `piece_size`, 텍스트 변환, `full_rows`를 명세에 맞게 수정했습니다.
- **중간 — 계산:** 보드 분석 함수와 점수·레벨·중력·콤보 함수를 수정했습니다. 레벨 주기는 상수의 8이 아니라 함수 명세의 **10줄**로 통일했습니다. `bag_sequence`는 시드와 정확한 개수, 음수 예외를 적용했습니다.
- **수정 불필요 — 리소스 해제:** 제공 코드에는 파일·네트워크 등 별도로 해제할 외부 리소스가 없습니다. 큰 `count`의 7-bag 결과는 반환 계약상 메모리에 전체 보유됩니다.
- **미확인:** 직사각형 보드·조각을 전제로 합니다. 경계값, 입력 불변성, 동시 접근 정책과 기존 호출자 호환성에 대한 실행 및 회귀 테스트는 하지 않았습니다.

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트.
top은 행, left는 열(0부터). 보드와 조각은 직사각형이라고 가정한다.
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않는다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.

GameState를 여러 스레드에서 공유할 때는 호출자가 접근을 동기화해야 한다.
"""
import random

PIECES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[1, 1, 1], [0, 1, 0]],
    "S": [[1, 1, 0], [0, 1, 1]],
    "Z": [[0, 1, 1], [1, 1, 0]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}
LINE_SCORES = [0, 40, 100, 300, 1000]
LINES_PER_LEVEL = 10


# ---------------------------------------------------------------- 보드
def new_board(rows=20, cols=10):
    """빈 보드. rows·cols는 1 이상 정수, 아니면 ValueError."""
    if (
        not isinstance(rows, int)
        or isinstance(rows, bool)
        or not isinstance(cols, int)
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
    """블록은 '#', 빈칸은 '.'으로 한 줄씩, 줄 사이는 '\\n'."""
    return "\n".join(
        "".join("#" if cell else "." for cell in row) for row in board
    )


def text_to_board(text):
    """board_to_text의 역변환. 빈 문자열, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError."""
    if not text:
        raise ValueError("empty text")
    lines = text.split("\n")
    width = len(lines[0])
    if width == 0 or any(len(line) != width for line in lines):
        raise ValueError("ragged or empty board text")
    if any(ch not in "#." for line in lines for ch in line):
        raise ValueError("invalid board character")
    return [[1 if ch == "#" else 0 for ch in line] for line in lines]


# ---------------------------------------------------------------- 조각
def rotate_cw(piece):
    """시계 방향 90도: 위쪽 행이 오른쪽 열이 된다."""
    return [list(row) for row in zip(*piece[::-1])]


def rotate_ccw(piece):
    """반시계 방향 90도: 위쪽 행이 왼쪽 열이 된다(뒤집힌 순서)."""
    return [list(row) for row in zip(*piece)][::-1]


def rotate_180(piece):
    """180도: 행 순서와 각 행의 칸 순서를 모두 뒤집는다."""
    return [row[::-1] for row in reversed(piece)]


def piece_cells(piece):
    """블록 칸의 (행, 열) 목록(행 우선, 왼쪽부터)."""
    return [
        (r, c)
        for r, row in enumerate(piece)
        for c, cell in enumerate(row)
        if cell
    ]


def trim_piece(piece):
    """바깥쪽의 빈 행·빈 열을 잘라낸다. 블록이 하나도 없으면 ValueError."""
    cells = piece_cells(piece)
    if not cells:
        raise ValueError("piece has no blocks")
    top = min(r for r, _ in cells)
    bottom = max(r for r, _ in cells)
    left = min(c for _, c in cells)
    right = max(c for _, c in cells)
    return [row[left:right + 1] for row in piece[top:bottom + 1]]


def piece_size(piece):
    """(높이, 너비). 빈 조각의 크기는 (0, 0)."""
    return len(piece), len(piece[0]) if piece else 0


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True(빈칸은 밖에 있어도 된다)."""
    rows = len(board)
    cols = len(board[0]) if board else 0
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
        raise ValueError("piece cannot be placed")
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
    kept = [row[:] for row in board if not row or not all(row)]
    cleared = len(board) - len(kept)
    return [[0] * cols for _ in range(cleared)] + kept, cleared


def drop_row(board, piece, left, top=1):
    """top에서 아래로 떨어뜨렸을 때 멈추는 행.

    시작 위치에 놓을 수 없거나 조각에 블록이 없으면 ValueError.
    """
    if not piece_cells(piece):
        raise ValueError("piece has no blocks")
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed at the starting position")
    while can_place(board, piece, top + 1, left):
        top += 1
    return top


def hard_drop(board, piece, left, top=1):
    """끝까지 떨어뜨려 놓고 줄을 지운 (새 보드, 떨어진 칸 수, 지운 행 수)."""
    landing = drop_row(board, piece, left, top)
    placed_board = place(board, piece, landing, left)
    cleared_board, cleared = clear_lines(placed_board)
    return cleared_board, landing - top, cleared


def shift(board, piece, top, left, dx):
    """좌우로 dx칸 옮길 수 있으면 새 left, 막히면 원래 left(한 번에 dx칸, 중간 칸은 보지 않는다)."""
    if can_place(board, piece, top, left + dx):
        return left + dx
    return left


def wall_kick(board, piece, top, left, offsets=((0, -1), (0, 0), (0, 1), (-1, 0))):
    """offsets(행, 열 이동)를 순서대로 시도해 처음 놓을 수 있는 (top, left). 모두 막히면 None."""
    for dy, dx in offsets:
        if can_place(board, piece, top + dy, left + dx):
            return top + dy, left + dx
    return None


def is_game_over(board, piece, left):
    """맨 위(top=0)에 조각을 놓을 수 없으면 True."""
    return not can_place(board, piece, 0, left)


# ---------------------------------------------------------------- 보드 분석
def column_heights(board):
    """열마다 맨 위 블록부터 바닥까지의 높이(블록이 없으면 0)."""
    rows = len(board)
    cols = len(board[0]) if board else 0
    heights = []
    for x in range(cols):
        height = 0
        for y in range(rows):
            if board[y][x]:
                height = rows - y
                break
        heights.append(height)
    return heights


def aggregate_height(board):
    """열 높이의 합."""
    return sum(column_heights(board))


def max_height(board):
    """가장 높은 열의 높이. 열이 없으면 0."""
    return max(column_heights(board), default=0)


def count_holes(board):
    """구멍 수: 어떤 열에서 블록 아래에 있는 빈칸."""
    rows = len(board)
    cols = len(board[0]) if board else 0
    holes = 0
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
    return sum(abs(a - b) for a, b in zip(heights, heights[1:]))


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).

    cleared가 0~4의 정수가 아니거나 level이 음수면 ValueError.
    """
    if (
        not isinstance(cleared, int)
        or isinstance(cleared, bool)
        or not 0 <= cleared <= 4
    ):
        raise ValueError("cleared must be an integer between 0 and 4")
    if level < 0:
        raise ValueError("level must not be negative")
    return LINE_SCORES[cleared] * (level + 1)


def level_for_lines(total_lines):
    """누적 줄 수로 레벨(10줄마다 1). 음수면 ValueError."""
    if total_lines < 0:
        raise ValueError("total_lines must not be negative")
    return total_lines // LINES_PER_LEVEL


def lines_to_next_level(total_lines):
    """다음 레벨까지 남은 줄 수(1~10). 누적 줄 수가 음수면 ValueError."""
    if total_lines < 0:
        raise ValueError("total_lines must not be negative")
    return LINES_PER_LEVEL - total_lines % LINES_PER_LEVEL


def gravity_frames(level):
    """한 칸 떨어지는 데 걸리는 프레임: 48 - 5*level, 최소 1."""
    return max(1, 48 - 5 * level)


def combo_bonus(combo, level):
    """연속으로 줄을 지운 횟수 combo(1부터)의 보너스 = 50 * combo * (level + 1). combo가 0 이하면 0."""
    if combo <= 0:
        return 0
    return 50 * combo * (level + 1)


def bag_sequence(count, seed):
    """7-bag 조각 목록: 7종을 한 묶음씩 섞어 이어 붙인 앞 count개.

    seed가 같으면 같은 순서다. count가 음수이거나 정수가 아니면 ValueError.
    반환 조각은 PIECES 및 서로 다른 반환 조각과 행을 공유하지 않는다.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be a non-negative integer")
    rng = random.Random(seed)
    sequence = []
    while len(sequence) < count:
        bag = list(PIECES)
        rng.shuffle(bag)
        for name in bag:
            if len(sequence) == count:
                break
            sequence.append([row[:] for row in PIECES[name]])
    return sequence


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다.

    기본 상태는 인스턴스마다 따로 가진다. 공유 인스턴스의 동시 접근과
    명시적으로 전달한 로그의 공유는 호출자가 동기화해야 한다.
    """

    def __init__(self, level=0, log=None):
        """시작 레벨과 선택적 로그를 받는다. 음수 레벨은 ValueError."""
        if level < 0:
            raise ValueError("level must not be negative")
        self.score = 0
        self.lines = 0
        self.start_level = level
        self.combo = 0
        self.held = None
        self.can_hold = True
        self.log = [] if log is None else log

    @property
    def level(self):
        """시작 레벨 + 누적 줄로 오른 레벨."""
        return self.start_level + level_for_lines(self.lines)

    def record_clear(self, cleared):
        """조각 하나를 놓은 뒤 지운 줄 수를 반영한다. 점수는 반영 전 레벨로 계산한다.

        지웠으면 combo += 1 후 줄 점수 + 콤보 보너스(2번째 연속부터, combo-1 기준),
        못 지웠으면 combo = 0. 놓을 때마다 다시 보관할 수 있게 된다.
        반환: 이번에 얻은 점수.
        """
        level = self.level
        gained = score_for_lines(cleared, level)
        new_combo = self.combo + 1 if cleared > 0 else 0
        if new_combo > 1:
            gained += combo_bonus(new_combo - 1, level)

        self.log.append((cleared, gained))
        self.combo = new_combo
        self.lines += cleared
        self.score += gained
        self.can_hold = True
        return gained

    def hold(self, current):
        """현재 조각 이름을 보관하고 이전 보관 조각(없으면 None)을 돌려준다.

        한 번 놓기 전에 두 번 보관하면 ValueError.
        """
        if not self.can_hold:
            raise ValueError("hold has already been used")
        previous = self.held
        self.held = current
        self.can_hold = False
        return previous
```