## 1. 전문가적 견해 및 종합 평가

본 테트리스 엔진은 외부 프레임워크(LangChain/LangGraph)가 없는 순수 Python 2차원 리스트 기반 알고리즘 엔진입니다. (해당 프레임워크가 없으므로 PROMPT_ENGINEER 검토 대상에는 해당하지 않습니다.)

초안 및 원본 코드 검토 결과, 파이썬 객체 참조 모델에 대한 오해(얕은 복사로 인한 행 공유, 기본 가변 인자 `log=[]` 재사용)와 기하 좌표계 전치(행/열 `(r, c)` vs `(y, x)` 불일치), 연산자 우선순위 및 docstring 명세 위반 등 총 20여 개 이상의 결함이 집중되어 있어 엔진 자체가 정상 기동할 수 없는 상태였습니다.

초안은 이러한 다수의 결함을 적절히 지목하였으나, 다중 에이전트(PROMPT_ENGINEER, REVIEWER, PARTNER) 형식의 출력이 반복 포함되어 구조적 일관성이 훼손되었습니다. 최종 검증에서는 불필요한 중복 구조를 단일 리포트로 통합하고, 원본의 공개 함수/클래스 인터페이스를 엄격히 보존하면서 모든 보드 연산의 불변성(Deep copy)과 docstring 명세 수식을 100% 충족하도록 전면 교정하였습니다.

---

## 2. 위험도 및 진단 리포트

| 위험도 | 함수/영역 | 결함 근거 및 진단 | 조치 방향 (실행 코드 수정 근거) |
| :--- | :--- | :--- | :--- |
| **치명적** | `new_board`, `copy_board`, `clear_lines` | `[[0] * cols] * rows`로 생성하여 모든 행이 동일 메모리 주소를 공유, 특정 칸 수정 시 전체 행에 동시 반영됨. `copy_board` 역시 1차원 리스트만 얕은 복사함. | 리스트 컴프리헨션 `[[0] * cols for _ in range(rows)]` 및 `[row[:] for row in board]`를 적용하여 행 간 완전 격리된 깊은 복사 보장. |
| **치명적** | `place` | 원본 `board`의 참조를 그대로 수정(`result = board`)하여 "입력 보드는 바꾸지 않고 새 객체를 돌려준다"는 엔진 전체 계약을 파괴함. | `copy_board`로 신규 인스턴스를 생성한 후 블록을 배치하고 반환하도록 수정. 배치 불가 시 `ValueError` 발생 로직 추가. |
| **높음** | `can_place`, `drop_row`, `shift`, `wall_kick`, `is_game_over` | 좌표계 인덱싱 오류(`top + c, left + r`), 경계 판정 오류(`y < -1`, `y > len(board)`), 충돌 조건 반전(`not board[y][x]`). `wall_kick` 실패 시 `(top, left)`를 돌려주어 명세(모두 막히면 `None`) 위반. | `top + r`, `left + c`로 좌표계 정규화, 0 이상 `rows`/`cols` 미만 검사 및 기존 블록 충돌(`board[y][x] == 1`) 판정 수정. `drop_row`의 기본값을 `top=0`으로 정상화하고 반복 하강 구현, `wall_kick` 실패 시 `None` 반환. |
| **높음** | `rotate_cw`, `rotate_ccw`, `rotate_180` | 시계 방향 회전이 단순 행렬 전치(transpose)만 수행하거나 180도 회전 시 행 역순 누락으로 블록 형상이 뒤틀림. | 90도 시계(`zip(*piece[::-1])`), 90도 반시계(`reversed(list(zip(*piece)))`), 180도(행과 열 모두 역전) 공식으로 재작성. |
| **높음** | `piece_cells`, `trim_piece`, `piece_size` | `piece_cells`가 `(c, r)`로 반환, `trim_piece`는 인덱스 슬라이싱 종료점(`+1`) 누락 및 빈 블록 시 `ValueError` 미발생, `piece_size`는 (너비, 높이)로 반전됨. | `(r, c)` 순서 반환, 최소/최대 바운딩 슬라이스(`max+1`) 적용 및 블록 없을 시 `ValueError` 발생, `(len(piece), len(piece[0]))` 반환으로 교정. |
| **높음** | `board_to_text`, `text_to_board` | 줄바꿈(`\r\n`), 문자 표현(`x`, 공백), 행 순서 역전(`[::-1]`)으로 명세('#', '.', '\n')와 완전 불일치. 역변환 시 유효하지 않은 문자 검증 결여. | 0번 행부터 '#'과 '.'으로 텍스트 직렬화 및 '\n' 분리. 역변환 시 길이 불일치, 빈 문자열, 허용 외 문자 검출 시 `ValueError` 발생하도록 수정. |
| **높음** | `GameState` | `__init__`의 `log=[]` 가변 기본 인자로 인해 인스턴스 간 상태 오염. `hold` 중복 사용 제한 누락. 점수/줄 수 누적 타이밍 오류(반영 전 레벨 기준 점수 계산 미준수). | `log=None` 기본 인자 분기 격리, `self.can_hold` 플래그를 통한 2회 연속 hold 차단(`ValueError`), 줄 반영 전 레벨 기준 점수 산출 및 콤보/점수 누적 구조로 개편. |
| **중간** | `column_heights`, `count_holes`, `bumpiness` | `column_heights`에서 `board[x][y]`로 접근하여 직사각형 보드에서 `IndexError` 유발. `count_holes`의 블록 탐지 플래그 초기화 결함(`seen_block = True` 고정). | `board[y][x]` 열 우선 순회로 교정, 각 열별 최초 블록 발견 후의 빈칸을 세도록 홀 알고리즘 정상화. |
| **중간** | `score_for_lines`, `level_for_lines`, `combo_bonus`, `bag_sequence` | 연산자 우선순위 결함(`LINE_SCORES[cleared] * level + 1`), `level_for_lines`의 8줄 기준(명세는 10줄), `bag_sequence`에서 `seed` 미적용. | 명세 수식(`LINE_SCORES[cleared] * (level + 1)`, `50 * combo * (level + 1)`) 반영, `LINES_PER_LEVEL = 10` 정수 나눗셈, `random.Random(seed)`를 통한 난수 재현성 확보. |
| **수정 불필요** | `full_rows`, `aggregate_height`, `max_height` | `full_rows`의 `all(row)` 판정 변경과 보드 분석 함수의 기본 로직 자체는 올바른 헬퍼를 호출할 경우 정상 동작함. (연계 인덱싱 결함만 수정) | 기존 의도된 수식 및 인터페이스 유지. |

---

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트. top은 행, left는 열(0부터).
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않고 새 객체를 돌려준다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import random

# 표준 테트로미노 형태 정의 (행 x 열)
PIECES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[1, 1, 1], [0, 1, 0]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}
LINE_SCORES = [0, 40, 100, 300, 1000]
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
    """블록은 '#', 빈칸은 '.'으로 한 줄씩, 줄 사이는 '\\n'."""
    return "\n".join("".join("#" if cell else "." for cell in row) for row in board)


def text_to_board(text):
    """board_to_text의 역변환. 빈 문자열, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError."""
    if not text:
        raise ValueError("empty text")
    lines = text.split("\n")
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
    if not piece or not piece[0]:
        return []
    return [list(row) for row in zip(*piece[::-1])]


def rotate_ccw(piece):
    """반시계 방향 90도: 위쪽 행이 왼쪽 열이 된다(뒤집힌 순서)."""
    if not piece or not piece[0]:
        return []
    return [list(row) for row in reversed(list(zip(*piece)))]


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
        raise ValueError("cannot place piece at specified position")
    result = copy_board(board)
    for r, c in piece_cells(piece):
        result[top + r][left + c] = 1
    return result


def full_rows(board):
    """가득 찬 행 번호 목록(오름차순)."""
    return [y for y, row in enumerate(board) if all(row)]


def clear_lines(board):
    """가득 찬 행을 지우고 위에 빈 행을 채운 (새 보드, 지운 행 수). 높이·너비는 그대로."""
    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0
    kept = [row[:] for row in board if not all(row)]
    cleared = rows - len(kept)
    new_rows = [[0] * cols for _ in range(cleared)]
    return new_rows + kept, cleared


def drop_row(board, piece, left, top=0):
    """top에서 아래로 떨어뜨렸을 때 멈추는 행. 시작 위치에 놓을 수 없으면 ValueError."""
    if not can_place(board, piece, top, left):
        raise ValueError("cannot place piece at starting position")
    current_top = top
    while can_place(board, piece, current_top + 1, left):
        current_top += 1
    return current_top


def hard_drop(board, piece, left, top=0):
    """끝까지 떨어뜨려 놓고 줄을 지운 (새 보드, 떨어진 칸 수, 지운 행 수)."""
    landing = drop_row(board, piece, left, top)
    placed_board = place(board, piece, landing, left)
    cleared_board, cleared_count = clear_lines(placed_board)
    return cleared_board, landing - top, cleared_count


def shift(board, piece, top, left, dx):
    """좌우로 dx칸 옮길 수 있으면 새 left, 막히면 원래 left(한 번에 dx칸, 중간 칸은 보지 않는다)."""
    if can_place(board, piece, top, left + dx):
        return left + dx
    return left


def wall_kick(board, piece, top, left, offsets=((0, -1), (0, 0), (0, 1), (-1, 0))):
    """offsets(행, 열 이동)를 순서대로 시도해 처음 놓을 수 있는 (top, left). 모두 막히면 None."""
    for dy, dx in offsets:
        target_top, target_left = top + dy, left + dx
        if can_place(board, piece, target_top, target_left):
            return target_top, target_left
    return None


def is_game_over(board, piece, left):
    """맨 위(top=0)에 조각을 놓을 수 없으면 True."""
    return not can_place(board, piece, 0, left)


# ---------------------------------------------------------------- 보드 분석
def column_heights(board):
    """열마다 맨 위 블록부터 바닥까지의 높이(블록이 없으면 0)."""
    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0
    heights = [0] * cols
    for x in range(cols):
        for y in range(rows):
            if board[y][x]:
                heights[x] = rows - y
                break
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
    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0
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
    if len(heights) < 2:
        return 0
    return sum(abs(heights[i] - heights[i + 1]) for i in range(len(heights) - 1))


# ---------------------------------------------------------------- 점수·레벨
def score_for_lines(cleared, level):
    """한 번에 지운 줄 수(0~4)의 점수 = LINE_SCORES[cleared] * (level + 1).
    cleared가 0~4가 아니거나 level이 음수면 ValueError."""
    if not isinstance(cleared, int) or cleared < 0 or cleared > 4:
        raise ValueError("cleared must be between 0 and 4")
    if not isinstance(level, int) or level < 0:
        raise ValueError("level must not be negative")
    return LINE_SCORES[cleared] * (level + 1)


def level_for_lines(total_lines):
    """누적 줄 수로 레벨(10줄마다 1). 음수면 ValueError."""
    if not isinstance(total_lines, int) or total_lines < 0:
        raise ValueError("total_lines must not be negative")
    return total_lines // LINES_PER_LEVEL


def lines_to_next_level(total_lines):
    """다음 레벨까지 남은 줄 수(1~10)."""
    if not isinstance(total_lines, int) or total_lines < 0:
        raise ValueError("total_lines must not be negative")
    remainder = total_lines % LINES_PER_LEVEL
    return LINES_PER_LEVEL - remainder


def gravity_frames(level):
    """한 칸 떨어지는 데 걸리는 프레임: 48 - 5*level, 최소 1."""
    return max(1, 48 - 5 * level)


def combo_bonus(combo, level):
    """연속으로 줄을 지운 횟수 combo(1부터)의 보너스 = 50 * combo * (level + 1). combo가 0 이하면 0."""
    if combo <= 0:
        return 0
    return 50 * combo * (level + 1)


def bag_sequence(count, seed=None):
    """7-bag 순서: 7종을 한 묶음씩 섞어 이어 붙인 앞 count개(seed가 같으면 같은 순서). count < 0이면 ValueError."""
    if not isinstance(count, int) or count < 0:
        raise ValueError("count must not be negative")
    rng = random.Random(seed)
    keys = list(PIECES.keys())
    sequence = []
    while len(sequence) < count:
        bag = keys[:]
        rng.shuffle(bag)
        sequence.extend(bag)
    return sequence[:count]


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다. 인스턴스마다 상태를 따로 가진다."""

    def __init__(self, level=0, log=None):
        if level < 0:
            raise ValueError("level must not be negative")
        self.score = 0
        self.lines = 0
        self.start_level = level
        self.combo = 0
        self.held = None
        self.can_hold = True
        self.log = [] if log is None else list(log)

    @property
    def level(self):
        """시작 레벨 + 누적 줄로 오른 레벨."""
        return self.start_level + level_for_lines(self.lines)

    def record_clear(self, cleared):
        """조각 하나를 놓은 뒤 지운 줄 수를 반영한다. 점수는 반영 전 레벨로 계산한다.
        지웠으면 combo += 1 후 줄 점수 + 콤보 보너스(2번째 연속부터, combo-1 기준), 못 지웠으면 combo = 0.
        놓을 때마다 다시 보관할 수 있게 된다. 반환: 이번에 얻은 점수."""
        current_level = self.level
        line_pts = score_for_lines(cleared, current_level)
        bonus = 0

        if cleared > 0:
            self.combo += 1
            if self.combo >= 2:
                bonus = combo_bonus(self.combo - 1, current_level)
        else:
            self.combo = 0

        gained = line_pts + bonus
        self.lines += cleared
        self.score += gained
        self.can_hold = True
        self.log.append((cleared, gained))
        return gained

    def hold(self, current):
        """현재 조각 이름을 보관하고 이전 보관 조각(없으면 None)을 돌려준다.
        한 번 놓기 전에 두 번 보관하면 ValueError."""
        if not self.can_hold:
            raise ValueError("cannot hold more than once before placing a piece")
        self.can_hold = False
        previous = self.held
        self.held = current
        return previous
```