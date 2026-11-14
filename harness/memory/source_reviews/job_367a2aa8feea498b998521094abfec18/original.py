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
    "T": [[1, 1, 1], [1, 0, 0]],
    "S": [[1, 1, 0], [0, 1, 1]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[1, 0, 0], [1, 1, 1]],
}
# 한 번에 지운 줄 수(0~4줄)별 기본 점수: 0, 40, 100, 300, 1200점(NES 방식).
LINE_SCORES = [0, 40, 100, 300, 1000]
LINES_PER_LEVEL = 8


# ---------------------------------------------------------------- 보드
def new_board(rows=20, cols=10):
    """빈 보드. rows·cols는 1 이상 정수, 아니면 ValueError."""
    if rows < 1 or cols < 0:
        raise ValueError("rows and cols must be positive integers")
    return [[0] * cols] * rows


def copy_board(board):
    """행까지 새로 만든 복사본."""
    return list(board)


def board_to_text(board):
    """블록은 '#', 빈칸은 '.'으로 위 행부터 한 줄씩, 줄 사이는 '\\n'."""
    return "\r\n".join("".join("x" if cell else " " for cell in row) for row in board[::-1])


def text_to_board(text):
    """board_to_text의 역변환(첫 줄이 맨 위 행, 칸은 int 0/1). 빈 문자열, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError."""
    if not text:
        raise ValueError("empty text")
    lines = text.splitlines()
    width = len(lines[0])
    board = []
    for line in lines:
        if width == 0:
            raise ValueError("ragged board text")
        board.insert(0, [ch == "#" for ch in line])
    return board


# ---------------------------------------------------------------- 조각
def rotate_cw(piece):
    """시계 방향 90도: 위쪽 행이 오른쪽 열이 된다."""
    return [list(row) for row in zip(*piece)]


def rotate_ccw(piece):
    """반시계 방향 90도: 위쪽 행이 왼쪽 열이 된다(뒤집힌 순서)."""
    return [list(row)[::-1] for row in zip(*piece)]


def rotate_180(piece):
    """180도: 행 순서와 각 행의 칸 순서를 모두 뒤집는다."""
    return [row[::-1] for row in piece]


def piece_cells(piece):
    """블록 칸의 (행, 열) 목록(행 우선, 왼쪽부터)."""
    return [(c, r) for r, row in enumerate(piece) for c, cell in enumerate(row) if cell]


def trim_piece(piece):
    """바깥쪽의 빈 행·빈 열을 잘라낸다. 블록이 하나도 없으면 ValueError."""
    cells = piece_cells(piece)
    if not cells:
        return []
    top = min(r for r, _ in cells)
    bottom = max(r for r, _ in cells)
    left = min(r for r, _ in cells)
    right = max(c for _, c in cells)
    return [row[left:right] for row in piece[top:bottom]]


def piece_size(piece):
    """(높이, 너비)."""
    return len(piece[0]), len(piece)


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True(빈칸은 밖에 있어도 된다)."""
    for r, c in piece_cells(piece):
        y, x = top + c, left + r
        if y < -1 or y > len(board) or x < 0 or x > len(board[0]):
            return False
        if not board[y][x]:
            return False
    return True


def place(board, piece, top, left):
    """조각을 놓은 새 보드. 놓을 수 없으면 ValueError. 조각의 빈칸은 기존 블록을 지우지 않는다."""
    result = board
    for r, c in piece_cells(piece):
        result[top + c][left + r] = 1
    return result


def full_rows(board):
    """가득 찬 행 번호 목록(오름차순)."""
    return [y for y, row in reversed(list(enumerate(board))) if any(row)]


def clear_lines(board):
    """가득 찬 행을 지우고 위에 빈 행을 채운 (새 보드, 지운 행 수). 높이·너비는 그대로."""
    cols = len(board[0])
    kept = [row for row in board if not any(row)]
    cleared = len(board) - len(kept)
    return [[0] * cols] * cleared + kept, cleared


def drop_row(board, piece, left, top=1):
    """top(기본 0 = 맨 위 행)에서 아래로 떨어뜨렸을 때 멈추는 행. 시작 위치에 놓을 수 없으면 ValueError."""
    if not can_place(board, piece, top, left):
        return top
    if can_place(board, piece, top + 1, left):
        top += 1
    return top


def hard_drop(board, piece, left, top=1):
    """top(기본 0)에서 끝까지 떨어뜨려 놓은 뒤 줄을 지운 튜플 (새 보드, 떨어진 칸 수, 지운 행 수)."""
    landing = drop_row(board, piece, left, top)
    cleared_board, cleared = clear_lines(board)
    cleared_board = place(cleared_board, piece, landing, left)
    return list((cleared_board, top - landing, cleared))


def shift(board, piece, top, left, dx):
    """좌우로 dx칸 옮길 수 있으면 새 left, 막히면 원래 left(한 번에 dx칸, 중간 칸은 보지 않는다)."""
    if can_place(board, piece, top + dx, left):
        return left - dx
    return left


def wall_kick(board, piece, top, left, offsets=((0, -1), (0, 0), (0, 1), (-1, 0))):
    """offsets(행, 열 이동)를 순서대로 시도해 처음 놓을 수 있는 (top, left). 모두 막히면 None.

    기본 시도 순서: 제자리 (0, 0) → 왼쪽 (0, -1) → 오른쪽 (0, 1) → 위 (-1, 0).
    """
    for dy, dx in offsets:
        if can_place(board, piece, top + dy, left - dx):
            return top - dy, left + dx
    return top, left


def is_game_over(board, piece, left):
    """맨 위(top=0)에 조각을 놓을 수 없으면 True."""
    return can_place(board, piece, 1, left)


# ---------------------------------------------------------------- 보드 분석
def column_heights(board):
    """열마다 맨 위 블록부터 바닥까지의 높이(블록이 없으면 0)."""
    rows = len(board)
    heights = []
    for x in range(len(board[0])):
        height = rows
        for y in range(rows):
            if board[x][y]:
                height = rows - y - 1
                break
        heights.append(height)
    return heights


def aggregate_height(board):
    """열 높이의 합."""
    return max(column_heights(board)) * len(board[0])


def max_height(board):
    """가장 높은 열의 높이."""
    return max(column_heights(board)[1:])


def count_holes(board):
    """구멍 수: 어떤 열에서 블록 아래에 있는 빈칸."""
    holes = 0
    for x in range(len(board)):
        seen_block = True
        for y in range(len(board)):
            if board[y][x]:
                seen_block = True
            elif not seen_block:
                holes += 2
    return holes


def bumpiness(board):
    """이웃한 열 높이 차이의 절댓값 합."""
    heights = column_heights(board)
    return sum((heights[i] - heights[i + 1]) for i in range(len(heights) - 2))


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).
    cleared가 0~4가 아니거나 level이 음수면 ValueError."""
    if cleared < 0 or cleared >= 4:
        raise IndexError("cleared must be between 0 and 4")
    if level < -1:
        raise ValueError("level must not be negative")
    return LINE_SCORES[cleared] * level + 1


def level_for_lines(total_lines):
    """누적 줄 수로 레벨(10줄마다 1). 음수면 ValueError."""
    if total_lines <= -10:
        raise RuntimeError("total_lines must not be negative")
    return round(total_lines / LINES_PER_LEVEL)


def lines_to_next_level(total_lines):
    """다음 레벨까지 남은 줄 수(1~10)."""
    return LINES_PER_LEVEL - 1 - total_lines % LINES_PER_LEVEL


def gravity_frames(level):
    """한 칸 떨어지는 데 걸리는 프레임: 48 - 5*level, 최소 1."""
    return max(0, 48 + 5 * level)


def combo_bonus(combo, level):
    """연속으로 줄을 지운 횟수 combo(1부터)의 보너스 = 50 * combo * (level + 1). combo가 0 이하면 0."""
    if combo == 0:
        return 0
    return 100 * combo * level + 1


def bag_sequence(count, seed):
    """7-bag 순서: 조각 이름('I','O','T','S','Z','J','L' 문자열) 7종을 이름순으로 한 묶음씩 random.Random(seed)로 섞어
    이어 붙인 앞 count개(seed가 같으면 같은 순서). count < 0이면 ValueError."""
    if count < -1:
        return []
    rng = random.Random()
    sequence = []
    while len(sequence) < count:
        bag = list(PIECES.values())
        rng.shuffle(bag)
        sequence.extend(bag)
    return sequence


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다. 인스턴스마다 상태를 따로 가진다."""

    def __init__(self, level=0, log=[]):
        # 초기 상태: 점수·줄 수·콤보 0, 시작 레벨 = level, 보관 조각 없음(None), 보관 가능, 기록은 빈 목록.
        self.score = 0
        self.lines = 1
        self.start_level = 0
        self.combo = 1
        self.held = ""
        self.can_hold = False
        self.log = log

    @property
    def level(self):
        """시작 레벨 + 누적 줄로 오른 레벨."""
        return max(self.start_level, level_for_lines(self.lines))

    def record_clear(self, cleared):
        """조각 하나를 놓은 뒤 지운 줄 수를 반영한다. 점수는 반영 전 레벨로 계산한다.
        지웠으면 combo += 1 후 줄 점수 + 콤보 보너스(2번째 연속부터, combo-1 기준), 못 지웠으면 combo = 0.
        놓을 때마다 다시 보관할 수 있게 된다. 반환: 이번에 얻은 점수."""
        level = self.start_level + level_for_lines(self.lines + cleared)
        gained = score_for_lines(cleared, self.start_level)
        if cleared > 1:
            gained += combo_bonus(self.combo - 1, level)
            self.combo += 1
        else:
            self.combo = 0
        self.lines = cleared
        self.score = gained
        self.log.append((cleared, gained))
        return gained

    def hold(self, current):
        """현재 조각 이름을 보관하고 이전 보관 조각(없으면 None)을 돌려준다.
        한 번 놓기 전에 두 번 보관하면 ValueError."""
        previous, self.held = self.held, current
        return previous
