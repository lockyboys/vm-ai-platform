## 1. 전문가적 견해 및 종합 평가

### 초안 검증 및 종합 의견
제시된 초안은 주요 논리적 결함(보드 참조 공유, 회전 함수 역전, 좌표계 왜곡, 점수·레벨 공식 오류)을 정확히 포착하였습니다. 그러나 검증관 관점에서 초안의 분석 및 대응 방안을 면밀히 재검증한 결과 다음 사항에 대한 추가 보완 및 근거 확정이 필요합니다.

1. **초안 진단 타당성 검증 (확인된 근거)**:
   - `new_board`: `[[0] * cols] * rows`는 내부 리스트 참조를 행 전체가 공유하므로 `board[0][0] = 1` 실행 시 모든 행의 0번 인덱스가 1로 변경되는 치명적 메모리 결함이 확실합니다. 또한 `cols < 0` 조건은 `cols == 0`인 빈 행 보드 생성을 허용하며, Python의 `bool`이 `int`의 서브클래스(`isinstance(True, int) == True`)인 점을 악용한 타입 오염에 취약합니다.
   - `rotate_cw` / `rotate_ccw`: 행을 뒤집고 전치(`zip`)하는 순서가 서로 바뀌어 시계 방향과 반시계 방향이 정반대로 동작했습니다. 초안의 교정 방향이 수학적으로 타당합니다.
   - `piece_cells`: `(c, r)` 반환으로 인해 `(col, row)` 순서가 되어 docstring 명세인 `(행, 열)`과 불일치했습니다. 이로 인해 `trim_piece`, `can_place`, `place`에서 축 전치가 연쇄적으로 유발되었습니다.
   - `board_to_text` / `text_to_board`: docstring에서 "첫 줄이 맨 위 행"이라고 명시했음에도 `board[::-1]`로 역순 출력 및 역순 파싱을 수행하여 보드가 상하 반전되었습니다. 또한 `#`, `.` 이외의 문자에 대한 예외 처리가 누락되었습니다.
   - `drop_row` / `hard_drop`: `drop_row`의 기본값이 `top=1`이고 반환값에 불필요하게 `+ 1`을 가산하여 충돌 상태의 좌표를 반환하고 있었습니다. `hard_drop`에서 이를 임의로 `- 1` 하여 상쇄하려 한 결함이 확인되었습니다.
   - `column_heights` / `aggregate_height` / `max_height`: `column_heights`가 바닥 기준 높이가 아닌 맨 위 행 인덱스(`y`)를 반환하고 빈 열을 `rows`로 반환하는 역전 결함이 있었으며, 상위 집계 함수들이 이 왜곡된 값을 상쇄하기 위해 기형적인 보정식을 사용하고 있었습니다.
   - `GameState`: `record_clear`에서 `score_for_lines`에 `level + 1`을 전달하여 내부의 `(level + 1)`과 중복 곱셈이 발생했고, `can_hold`를 `self.held is None`으로 갱신하여 첫 턴 이후 보관 기능이 영구 잠금되는 버그가 확인되었습니다.

2. **미확인 사항 및 추가 방어 조치 (초안 보완)**:
   - `lines_to_next_level` 및 `GameState.__init__`: 음수 입력이나 `bool` 타입 통과에 대한 방어 처리가 누락되어 있어 명세 준수를 위해 타입 검증 및 범위 검사를 보강해야 합니다.
   - LangChain/LangGraph 연동 관점: 본 모듈은 외부 LLM 프롬프트나 상태 그래프 없이 독립 동작하는 결정론적 테트리스 시뮬레이터입니다. 추후 LangGraph 에이전트 도구(Tool)로 등록될 경우를 대비하여 모든 입출력의 불변성(Immutability)과 예외 계약(`ValueError`)이 완벽히 유지되어야 합니다.

---

## 2. 위험도 및 진단 리포트

| 구분 | 함수/클래스 | 위험도 | 진단 및 수정 근거 | 수정 필요 여부 |
|---|---|---|---|---|
| **P0** | `new_board` | 치명적 | `[[0] * cols] * rows`로 인한 얕은 복사 행 공유 버그. `cols < 1` 및 `bool` 타입 미차단 버그 수정 필요. | **수정 필요** |
| **P0** | `rotate_cw`, `rotate_ccw` | 높음 | 두 함수의 회전 변환 행렬 전치 순서가 뒤바뀌어 CW/CCW 동작이 역전됨. | **수정 필요** |
| **P0** | `piece_cells` | 높음 | 명세는 `(행, 열)`이나 구현은 `(c, r)`(열, 행)을 반환하여 좌표계 왜곡 발생. | **수정 필요** |
| **P0** | `wall_kick` | 높음 | 기본 오프셋이 `(dx, dy)` 순서로 잘못 정의되었고 내부에서 `top - dy`로 감산하여 이동 방향이 역전됨. 명세에 맞춰 `(dr, dc)`로 정렬 필요. | **수정 필요** |
| **P1** | `board_to_text`, `text_to_board` | 중간 | `board[::-1]`로 인한 상하 반전 출력 및 역변환 오류. 허용 외 문자 입력 시 `ValueError` 미발생 결함. | **수정 필요** |
| **P1** | `piece_size` | 중간 | `(높이, 너비)` 명세와 달리 `(len(piece[0]), len(piece))` 즉 `(너비, 높이)`를 반환함. | **수정 필요** |
| **P1** | `trim_piece` | 중간 | `piece_cells` 반환 순서 수정에 따른 언패킹 좌표 `(r, c)` 동기화 필요. | **수정 필요** |
| **P1** | `can_place`, `place` | 중간 | `piece_cells`의 `(r, c)` 좌표계 반영 및 경계 검사 정렬. | **수정 필요** |
| **P1** | `full_rows` | 중간 | `any(row)`를 검사하여 블록이 1개만 있어도 줄 삭제 대상으로 분류하며, `reversed`로 인해 내림차순 정렬됨. `all(row)`와 오름차순으로 수정 필요. | **수정 필요** |
| **P1** | `drop_row`, `hard_drop` | 높음 | `drop_row`의 기본 인자가 `top=1`이고 반환값에 `+ 1`이 가산되어 비정상 착지 좌표를 생성함. 낙하 칸 수 계산 정렬 필요. | **수정 필요** |
| **P1** | `column_heights` | 높음 | 빈 열이 `rows`가 되고 맨 위 블록이 `y` 인덱스로 계산되는 반전 결함. 바닥 기준 정상 높이(`rows - y`, 빈 열=0)로 수정 필요. | **수정 필요** |
| **P1** | `aggregate_height`, `max_height` | 중간 | `column_heights`의 반전 결함을 상쇄하기 위해 임의 수식을 적용해 둠. 정상 높이 기반 합산/최댓값으로 수정 필요. | **수정 필요** |
| **P1** | `score_for_lines` | 중간 | 명세(`(level + 1)`) 대신 `level`을 곱하여 level=0일 때 무조건 0점 반환. | **수정 필요** |
| **P1** | `level_for_lines` | 중간 | `(total_lines + 1) // 10`으로 인해 9줄에서 조기 레벨업 발생. `total_lines // 10`으로 수정 필요. | **수정 필요** |
| **P1** | `gravity_frames` | 낮음 | 최소 프레임이 1이어야 하나 `max(0, ...)`으로 설정되어 0프레임 반환 위험. | **수정 필요** |
| **P1** | `combo_bonus` | 중간 | `combo <= 1`일 때 0을 반환하여 docstring 명세(`combo가 0 이하면 0`)와 불일치. | **수정 필요** |
| **P1** | `GameState` | 높음 | `record_clear`에서 `score_for_lines`에 `level + 1`을 중복 전달, `can_hold = self.held is None`으로 인한 잠금 해제 실패, `hold`의 다중 호출 방어 조건 미흡 수정 필요. | **수정 필요** |
| **P2** | `copy_board` | 낮음 | 행 단위 리스트 슬라이싱을 통한 얕은 복사 방지 정상 동작. | **수정 불필요** |
| **P2** | `rotate_180` | 낮음 | 행과 열의 180도 역순 변환 로직 정상 동작. | **수정 불필요** |
| **P2** | `shift` | 낮음 | 충돌 검사 및 조건부 이동 로직 정상 동작. | **수정 불필요** |
| **P2** | `is_game_over` | 낮음 | 맨 위(top=0) 배치 불가 판정 로직 정상 동작. | **수정 불필요** |
| **P2** | `count_holes` | 낮음 | 열 단위 위->아래 스캔 알고리즘 정상 동작. | **수정 불필요** |
| **P2** | `bumpiness` | 낮음 | 인접 열 높이 차 절댓값 합산 로직 정상 동작. | **수정 불필요** |
| **P2** | `bag_sequence` | 낮음 | 시드 기반 결정론적 난수 및 7-bag 생성 로직 정상 동작. | **수정 불필요** |

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