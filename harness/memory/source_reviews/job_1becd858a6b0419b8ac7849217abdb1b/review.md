## 1. 전문가적 견해 및 종합 평가

### 종합 검증 의견
제출된 초안은 입력 소스(`tetris_engine_gemini.py`)에 내재된 논리 결함, 메모리 참조 공유 문제, 테트리스 기본 규칙 위반 항목들을 정확히 진단하고 적절한 수정안을 제시했습니다.

- **메모리 및 객체 참조 모델**: `copy_board`에서의 얕은 복사(`list(board)`) 문제와 `clear_lines`에서의 리스트 복제 연산(`[[0] * cols] * cleared`)으로 인한 행 참조 공유 결함을 정확히 지적하고, 독자적인 행 리스트 인스턴스를 생성하도록 교정했습니다.
- **경계 검사 및 인덱싱**: `can_place`의 `y < -1` 조건이 유발하는 음수 인덱싱 버그, `shift`의 오프셋 부호 반전, `is_game_over`의 좌표 오차(`top=1`), `count_holes`의 행/열 인덱스 및 순회 방향 왜곡을 완벽히 바로잡았습니다.
- **상태 관리 및 게임 규칙**: `GameState` 내 `held` 초기화, 스왑 반환 로직, 콤보 증감 및 점수 계산 시 레벨 참조 오류를 docstring 명세에 맞추어 복원했습니다.
- **프롬프트 엔지니어 검토**: LangChain/LangGraph 등 LLM 프레임워크 요소가 없는 순수 알고리즘 엔진임을 올바르게 확인했습니다.

### 보완 및 주의 사항
- 초안의 수정 방향과 소스 코드는 요구 명세(NES 점수 체계, 7-bag 생성, 2차원 그리드 불변성)를 충실히 충족합니다.
- 공개 인터페이스(함수/클래스 시그니처 및 docstring 명세)가 누락 없이 보존되었음을 확인했습니다.

---

## 2. 위험도 및 진단 리포트

| 번호 | 함수 / 클래스 | 위험도 | 진단 및 수정 사유 |
|---|---|---|---|
| 1 | `copy_board` | **P0 (치명적)** | `list(board)`는 외부 컨테이너만 복사하므로 내부 행 리스트가 공유되어 원본 보드가 오염됨. `[row[:] for row in board]`로 2차원 깊은 복사 수행 필요. **(수정 완료)** |
| 2 | `clear_lines` | **P0 (치명적)** | `[[0] * cols] * cleared` 구문은 동일한 빈 행 참조를 반복 추가하여 한 행을 수정하면 채워진 모든 빈 행이 동시에 수정되는 심각한 참조 오염 발생. 컴프리헨션을 통한 독립 행 인스턴스 생성으로 수정. **(수정 완료)** |
| 3 | `can_place` | **P0 (치명적)** | `y < -1`로 인해 `y = -1`일 때 Python의 음수 인덱싱(`board[-1]`)이 작동하여 최하단 행과 비정상 검증됨. `y < 0`으로 경계 조건 수정. **(수정 완료)** |
| 4 | `full_rows` | **P0 (치명적)** | `any(row)`를 사용하여 한 칸만 차 있어도 가득 찬 행으로 판별함. `all(row)`로 조건 수정. **(수정 완료)** |
| 5 | `count_holes` | **P0 (치명적)** | 열 순회 범위에 행 길이(`len(board)`)를 사용하고 역순으로 순회하여 행/열 불일치 및 구멍 계산 왜곡 발생. 열 기준(`cols`)으로 위에서 아래로 순회하도록 수정. **(수정 완료)** |
| 6 | `GameState.record_clear` | **P0 (치명적)** | `cleared > 1`일 때만 콤보를 올려 1줄 클리어 시 콤보가 유지되지 않고, 점수 계산 시 시작 레벨(`self.start_level`)을 고정 전달하는 결함 존재. 1줄 이상(`cleared > 0`) 시 콤보 증가 및 반영 전 현재 레벨(`self.level`) 반영으로 수정. **(수정 완료)** |
| 7 | `GameState.hold` | **P0 (치명적)** | 이전 보관 조각 대신 방금 들어온 `current`를 그대로 반환함. 이전 조각 백업 후 새 조각 저장 및 이전 값 반환으로 수정. **(수정 완료)** |
| 8 | `board_to_text` | **P1 (높음)** | 명세(위 행부터 한 줄씩)와 달리 `board[::-1]`로 역순 출력하여 보드가 상하 반전됨. 정방향 순회로 수정. **(수정 완료)** |
| 9 | `trim_piece` | **P1 (높음)** | 블록이 없는 경우 명세는 `ValueError`를 요구하지만 빈 리스트(`[]`)를 반환함. `ValueError` 발생으로 수정. **(수정 완료)** |
| 10 | `shift` | **P1 (높음)** | `left - dx`로 계산하여 우측 이동 시 좌측으로 이동하는 등 방향이 반전됨. `left + dx`로 수정. **(수정 완료)** |
| 11 | `is_game_over` | **P1 (높음)** | 명세(`top=0`)와 달리 `top=1` 위치를 검사함. `top=0`으로 수정. **(수정 완료)** |
| 12 | `lines_to_next_level` | **P1 (높음)** | `(total_lines - 1)` 식은 `total_lines=0`일 때 음수 모듈러 연산으로 인해 잘못된 값을 반환할 수 있음. `LINES_PER_LEVEL - (total_lines % LINES_PER_LEVEL)`로 정규화. **(수정 완료)** |
| 13 | `gravity_frames` | **P1 (높음)** | `48 + 5 * level`로 작성되어 레벨이 오를수록 낙하 시간이 증가함. `max(1, 48 - 5 * level)`로 수정. **(수정 완료)** |
| 14 | `bag_sequence` | **P1 (높음)** | 7종 조각을 '이름순'으로 묶은 후 셔플해야 하는 명세를 위반(`PIECES` 사전 순서 의존)하며 요청 개수 슬라이싱이 누락됨. `sorted(PIECES)` 및 `[:count]` 슬라이싱 적용. **(수정 완료)** |
| 15 | `aggregate_height` | **P2 (중간)** | 0번 열을 누락(`[1:]`)하고 합산함. 전체 열 합산으로 수정. **(수정 완료)** |
| 16 | `GameState.__init__` | **P2 (중간)** | `self.held`가 명세(`None`)와 달리 빈 문자열(`""`)로 초기화됨. `None`으로 수정. **(수정 완료)** |
| 17 | `new_board`, `rotate_*`, `place`, `drop_row`, `hard_drop`, `wall_kick`, `column_heights`, `max_height`, `bumpiness`, `score_for_lines`, `level_for_lines`, `combo_bonus` | **수정 불필요** | 기존 구현이 명세 및 계약 조건을 충족하므로 불필요한 변경 없이 유지. |

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
    if not isinstance(rows, int) or not isinstance(cols, int) or rows < 1 or cols < 1:
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
    width = len(lines[0])
    board = []
    for line in lines:
        if len(line) != width or width == 0:
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
    return [row[left:right + 1] for row in piece[top:bottom + 1]]


def piece_size(piece):
    """(높이, 너비)."""
    return len(piece), len(piece[0])


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True(빈칸은 밖에 있어도 된다)."""
    rows = len(board)
    cols = len(board[0])
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
    cols = len(board[0])
    full = set(full_rows(board))
    kept = [row[:] for y, row in enumerate(board) if y not in full]
    cleared = len(board) - len(kept)
    new_rows = [[0] * cols for _ in range(cleared)]
    return new_rows + kept, cleared


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
    cols = len(board[0])
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
    """가장 높은 열의 높이."""
    return max(column_heights(board))


def count_holes(board):
    """구멍 수: 어떤 열에서 블록 아래에 있는 빈칸."""
    rows = len(board)
    cols = len(board[0])
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
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).
    cleared가 0~4가 아니거나 level이 음수면 ValueError."""
    if cleared < 0 or cleared > 4:
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
    """다음 레벨까지 남은 줄 수(1~10)."""
    if total_lines < 0:
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
    if count < 0:
        raise ValueError("count must not be negative")
    rng = random.Random(seed)
    sequence = []
    base_bag = sorted(PIECES.keys())
    while len(sequence) < count:
        bag = list(base_bag)
        rng.shuffle(bag)
        sequence.extend(bag)
    return sequence[:count]


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다. 인스턴스마다 상태를 따로 가진다."""

    def __init__(self, level=0):
        # 초기 상태: 점수·줄 수·콤보 0, 시작 레벨 = level, 보관 조각 없음(None), 보관 가능, 기록은 빈 목록.
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
        if cleared > 0:
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
        previous = self.held
        self.held = current
        self.can_hold = False
        return previous
```