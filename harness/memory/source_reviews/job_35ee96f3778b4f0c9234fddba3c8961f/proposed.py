"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트. top은 행, left는 열(0부터).
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않고 새 객체를 돌려준다.
보드와 조각은 직사각형 행렬이라고 가정한다.
GameState를 여러 스레드에서 공유할 때는 호출자가 접근을 직렬화해야 한다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
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
    return [list(row) for row in board]


def board_to_text(board):
    """블록은 '#', 빈칸은 '.'으로 한 줄씩, 줄 사이는 '\\n'."""
    return "\n".join(
        "".join("#" if cell else "." for cell in row)
        for row in board
    )


def text_to_board(text):
    """board_to_text의 역변환. 빈 문자열, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError."""
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
    return [list(row[left:right + 1]) for row in piece[top:bottom + 1]]


def piece_size(piece):
    """(높이, 너비). 빈 조각은 (0, 0)."""
    return len(piece), len(piece[0]) if piece else 0


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True(빈칸은 밖에 있어도 된다)."""
    for r, c in piece_cells(piece):
        y, x = top + r, left + c
        if y < 0 or y >= len(board) or x < 0 or x >= len(board[y]):
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
    if not board:
        return [], 0
    cols = len(board[0])
    kept = [list(row) for row in board if not (row and all(row))]
    cleared = len(board) - len(kept)
    return [[0] * cols for _ in range(cleared)] + kept, cleared


def drop_row(board, piece, left, top=1):
    """top에서 아래로 떨어뜨렸을 때 멈추는 행.

    시작 위치에 놓을 수 없거나 블록이 없는 조각이면 ValueError.
    """
    if not piece_cells(piece):
        raise ValueError("piece has no blocks")
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed at starting position")
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
    if not board:
        return []
    rows = len(board)
    heights = []
    for x in range(len(board[0])):
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
    if not board:
        return 0
    holes = 0
    for x in range(len(board[0])):
        seen_block = False
        for y in range(len(board)):
            if board[y][x]:
                seen_block = True
            elif seen_block:
                holes += 1
    return holes


def bumpiness(board):
    """이웃한 열 높이 차이의 절댓값 합."""
    heights = column_heights(board)
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).
    cleared가 0~4의 정수가 아니거나 level이 음수면 ValueError."""
    if not isinstance(cleared, int) or isinstance(cleared, bool) or not 0 <= cleared <= 4:
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
    """다음 레벨까지 남은 줄 수(1~10). 음수면 ValueError."""
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
    """7-bag 조각 행렬 순서의 앞 count개. 같은 seed면 같은 순서.

    count는 음수가 아닌 정수여야 한다. 반환 조각은 전역 조각과
    서로 행을 공유하지 않는다.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("count must be a non-negative integer")
    rng = random.Random(seed)
    sequence = []
    while len(sequence) < count:
        bag = list(PIECES.values())
        rng.shuffle(bag)
        remaining = count - len(sequence)
        sequence.extend(
            [list(row) for row in piece]
            for piece in bag[:remaining]
        )
    return sequence


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다.

    기본 로그는 인스턴스마다 따로 가진다. 명시적으로 전달한 로그는
    호출자의 목록을 사용한다. 동시 접근은 호출자가 직렬화해야 한다.
    """

    def __init__(self, level=0, log=None):
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
        지웠으면 combo += 1 후 줄 점수 + 콤보 보너스(2번째 연속부터, combo-1 기준), 못 지웠으면 combo = 0.
        놓을 때마다 다시 보관할 수 있게 된다. 반환: 이번에 얻은 점수."""
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
        한 번 놓기 전에 두 번 보관하면 ValueError."""
        if not self.can_hold:
            raise ValueError("hold already used for this piece")
        previous = self.held
        self.held = current
        self.can_hold = False
        return previous