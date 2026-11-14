## 1. 전문가적 견해 및 종합 평가

초안의 PARTNER 수정안은 제공된 소스의 주요 명세 위반을 대체로 해결합니다. 다만 `bag_sequence(float("inf"), seed)`는 여전히 종료되지 않아 수정이 필요합니다. 아래 소스에서는 조각 수를 음이 아닌 정수로 검증합니다.

판정은 **정적 검토 기준**입니다. 실제 파일, 호출부와 테스트는 확인하지 못했고 아래 코드도 실행하지 않았습니다. 경로 이름과 달리 제공된 코드에는 LangChain/LangGraph 사용이 보이지 않아 PROMPT_ENGINEER 설계 검토 대상은 아닙니다.

## 2. 위험도 및 진단 리포트

### 수정 반영

| 위험도 | 근거와 수정 |
|---|---|
| 높음 | `new_board`, `copy_board`, `clear_lines`의 행 공유와 `place`의 입력 변경을 제거합니다. `GameState.__init__`의 가변 기본 인자도 제거합니다. |
| 높음 | `piece_cells`, `can_place`, `place`의 행·열, 경계 및 충돌 판정을 바로잡습니다. `drop_row`, `hard_drop`, `shift`, `wall_kick`, `is_game_over`도 명세에 맞게 수정합니다. 빈 조각의 낙하는 무한 반복 대신 `ValueError`로 거부합니다. |
| 높음 | `GameState`의 초기 상태, 누적 점수·줄 수, 반영 전 레벨, 콤보와 보관 제한을 수정합니다. 잘못된 줄 수는 상태 변경 전에 거부합니다. |
| 중간 | 조각 상수, 텍스트 변환, 회전·트리밍·크기, 완성 행 판정과 보드 분석을 명세에 맞게 수정합니다. |
| 중간 | 점수·레벨 상수와 관련 함수의 공식 및 예외를 수정합니다. `bag_sequence`는 시드를 사용해 이름순 조각 이름을 섞고 요청 개수만 반환합니다. **초안과 달리 무한대 등 정수가 아닌 count도 거부**합니다. |

### 진단만 또는 미확인

- 같은 `GameState` 인스턴스나 입력 보드를 여러 스레드에서 동시에 변경하는 계약은 확인되지 않았습니다. 아래 구현은 이를 자체 동기화하지 않으므로 공유 시 호출자가 동기화해야 합니다.
- `GameState.log`는 계속 증가합니다. 보존 기간과 메모리 제한 요구는 미확인입니다. 큰 정수 `count`의 `bag_sequence` 역시 요청 크기에 비례해 메모리를 사용합니다.
- 제공된 코드에는 명시적으로 닫아야 할 파일·소켓 등의 리소스가 보이지 않아 해제 코드 수정은 불필요합니다.
- 직사각형 보드·조각을 전제로 합니다. 회귀 테스트, 입력 불변성, 경계값 및 동시 사용 검증은 **미실행**입니다.

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트.
top은 행, left는 열(0부터). 보드와 조각은 직사각형이라고 가정한다.
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않고 새 객체를 돌려준다.
동일한 GameState나 공유 입력을 동시에 변경할 때는 호출자가 동기화해야 한다.
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
    return [list(row) for row in board]


def board_to_text(board):
    """블록은 '#', 빈칸은 '.'으로 위 행부터 한 줄씩, 줄 사이는 '\\n'."""
    return "\n".join(
        "".join("#" if cell else "." for cell in row)
        for row in board
    )


def text_to_board(text):
    """board_to_text의 역변환(첫 줄이 맨 위 행, 칸은 int 0/1).

    빈 문자열, 빈 줄, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError.
    행 구분자는 '\\n'이다.
    """
    if not text:
        raise ValueError("empty text")
    lines = text.split("\n")
    width = len(lines[0])
    if width == 0:
        raise ValueError("empty board row")
    board = []
    for line in lines:
        if len(line) != width:
            raise ValueError("ragged board text")
        if any(ch not in "#." for ch in line):
            raise ValueError("invalid board character")
        board.append([1 if ch == "#" else 0 for ch in line])
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
    return [list(row[::-1]) for row in piece[::-1]]


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
    return [list(row[left:right + 1]) for row in piece[top:bottom + 1]]


def piece_size(piece):
    """(높이, 너비). 빈 조각의 크기는 (0, 0)."""
    return len(piece), len(piece[0]) if piece else 0


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True.

    조각의 빈칸은 밖에 있어도 된다. 블록이 없는 조각은 조건을 만족한다.
    """
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
    """조각을 놓은 새 보드. 놓을 수 없으면 ValueError.

    조각의 빈칸은 기존 블록을 지우지 않는다.
    """
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed")
    result = copy_board(board)
    for r, c in piece_cells(piece):
        result[top + r][left + c] = 1
    return result


def full_rows(board):
    """가득 찬 행 번호 목록(오름차순)."""
    return [y for y, row in enumerate(board) if all(row)]


def clear_lines(board):
    """가득 찬 행을 지우고 위에 빈 행을 채운 (새 보드, 지운 행 수).

    높이·너비는 그대로이며 반환 행은 입력 행과 공유하지 않는다.
    """
    cols = len(board[0]) if board else 0
    kept = [list(row) for row in board if not all(row)]
    cleared = len(board) - len(kept)
    return [[0] * cols for _ in range(cleared)] + kept, cleared


def drop_row(board, piece, left, top=0):
    """top(기본 0 = 맨 위 행)에서 떨어뜨렸을 때 멈추는 행.

    시작 위치에 놓을 수 없거나 조각에 블록이 없으면 ValueError.
    빈 조각은 무한 낙하를 방지하기 위해 거부한다.
    """
    if not piece_cells(piece):
        raise ValueError("piece has no blocks")
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed at the starting position")
    while can_place(board, piece, top + 1, left):
        top += 1
    return top


def hard_drop(board, piece, left, top=0):
    """top(기본 0)에서 끝까지 떨어뜨려 놓은 뒤 줄을 지운 튜플.

    반환값은 (새 보드, 떨어진 칸 수, 지운 행 수)다.
    시작 위치가 유효하지 않거나 블록이 없는 조각이면 ValueError.
    """
    landing = drop_row(board, piece, left, top)
    placed = place(board, piece, landing, left)
    cleared_board, cleared = clear_lines(placed)
    return cleared_board, landing - top, cleared


def shift(board, piece, top, left, dx):
    """좌우로 dx칸 옮길 수 있으면 새 left, 막히면 원래 left.

    한 번에 dx칸 이동하며 중간 칸은 보지 않는다.
    """
    if can_place(board, piece, top, left + dx):
        return left + dx
    return left


def wall_kick(board, piece, top, left, offsets=((0, 0), (0, -1), (0, 1), (-1, 0))):
    """offsets(행, 열 이동)를 순서대로 시도해 처음 놓을 수 있는 (top, left).

    모두 막히면 None.
    기본 시도 순서: 제자리 (0, 0) → 왼쪽 (0, -1) → 오른쪽 (0, 1) → 위 (-1, 0).
    """
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
    """가장 높은 열의 높이. 빈 보드에서는 0."""
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
    return sum(
        abs(heights[i] - heights[i + 1])
        for i in range(len(heights) - 1)
    )


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).

    cleared가 정수 0~4가 아니거나 level이 음수면 ValueError.
    """
    if (
        not isinstance(cleared, int)
        or isinstance(cleared, bool)
        or not 0 <= cleared <= 4
    ):
        raise ValueError("cleared must be between 0 and 4")
    if level < 0:
        raise ValueError("level must not be negative")
    return LINE_SCORES[cleared] * (level + 1)


def level_for_lines(total_lines):
    """누적 줄 수로 레벨(10줄마다 1). 음수면 ValueError."""
    if total_lines < 0:
        raise ValueError("total_lines must not be negative")
    return total_lines // LINES_PER_LEVEL


def lines_to_next_level(total_lines):
    """다음 레벨까지 남은 줄 수(1~10). 음수면 ValueError."""
    if total_lines < 0:
        raise ValueError("total_lines must not be negative")
    return LINES_PER_LEVEL - total_lines % LINES_PER_LEVEL


def gravity_frames(level):
    """한 칸 떨어지는 데 걸리는 프레임: 48 - 5*level, 최소 1."""
    return max(1, 48 - 5 * level)


def combo_bonus(combo, level):
    """연속 줄 삭제 combo(1부터)의 보너스 = 50 * combo * (level + 1).

    combo가 0 이하면 0.
    """
    if combo <= 0:
        return 0
    return 50 * combo * (level + 1)


def bag_sequence(count, seed):
    """7-bag 순서로 섞은 조각 이름을 앞 count개 반환한다.

    이름순으로 7종을 한 묶음씩 random.Random(seed)로 섞는다.
    count는 음이 아닌 정수여야 하며, 아니면 ValueError.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be a non-negative integer")
    rng = random.Random(seed)
    sequence = []
    while len(sequence) < count:
        bag = sorted(PIECES)
        rng.shuffle(bag)
        sequence.extend(bag[:count - len(sequence)])
    return sequence


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다.

    인스턴스마다 상태를 따로 가진다. 동일 인스턴스의 동시 변경은
    호출자가 동기화해야 한다.
    """

    def __init__(self, level=0, log=None):
        """초기 상태를 만든다. 음수 시작 레벨은 ValueError.

        전달된 기록은 복사한다.
        """
        if level < 0:
            raise ValueError("level must not be negative")
        self.score = 0
        self.lines = 0
        self.start_level = level
        self.combo = 0
        self.held = None
        self.can_hold = True
        self.log = list(log) if log is not None else []

    @property
    def level(self):
        """시작 레벨 + 누적 줄로 오른 레벨."""
        return self.start_level + level_for_lines(self.lines)

    def record_clear(self, cleared):
        """조각 하나를 놓은 뒤 지운 줄 수를 반영한다.

        점수는 반영 전 레벨로 계산한다. 지웠으면 combo += 1 후 줄 점수와
        콤보 보너스(2번째 연속부터, combo-1 기준)를 더한다.
        못 지웠으면 combo = 0. 놓을 때마다 다시 보관할 수 있게 된다.
        반환: 이번에 얻은 점수.
        """
        level = self.level
        gained = score_for_lines(cleared, level)
        next_combo = self.combo + 1 if cleared > 0 else 0
        if next_combo > 1:
            gained += combo_bonus(next_combo - 1, level)

        self.log.append((cleared, gained))
        self.combo = next_combo
        self.lines += cleared
        self.score += gained
        self.can_hold = True
        return gained

    def hold(self, current):
        """현재 조각 이름을 보관하고 이전 보관 조각(없으면 None)을 돌려준다.

        한 번 놓기 전에 두 번 보관하면 ValueError.
        """
        if not self.can_hold:
            raise ValueError("hold already used for this piece")
        previous = self.held
        self.held = current
        self.can_hold = False
        return previous
```