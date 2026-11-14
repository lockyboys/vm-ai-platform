## 1. 전문가적 견해 및 종합 평가

**검증 결론: 초안의 핵심 수정은 타당합니다.** 네 개 역할(PROMPT_ENGINEER·REVIEWER·BUG_HUNTER·PARTNER) 초안은 모두 같은 원인을 짚었고, 같은 실행 코드 변경을 제시했습니다. 최종본은 하나로 통합했고, 실행 코드 변경은 `text_to_board` 한 곳으로 한정했습니다.

**실패 원인 (근거: 실패 로그 + 소스 정적 추적)**
- 직전 수정안은 `splitlines()`를 `split("\n")`으로 바꿨습니다. 그러나 끝 개행을 버리는 분기(`if len(lines) > 1 and lines[-1] == "": lines.pop()`)는 그대로 남겼습니다.
- 그래서 `'#.\n'`은 `['#.', '']` → pop → `['#.']` → `[[1, 0]]`이 되어, 수정 전과 결과가 같았습니다.
- 이것이 통과 수가 187 → 187로 그대로였던 이유이며, 로그의 `('ok', [[1, 0]])`와 일치합니다.

**수정 근거 (명세)**
- docstring은 이 함수를 "`board_to_text`의 역변환"으로 정의하고, "길이가 다른 줄은 ValueError"라고 규정합니다.
- `board_to_text`는 `"\n".join(...)`을 쓰므로 끝 개행을 만들지 않습니다.
- 따라서 끝 개행이 남기는 빈 줄(폭 0)은 "길이가 다른 줄"이고, 거부하는 것이 명세에 맞습니다.

**수정 후 동작 대조 (정적 추적, 실행 미확인)**

| 입력 | 수정 전 | 수정 후 | 변화 |
|---|---|---|---|
| `'#.\n'` | `[[1, 0]]` | `ValueError("ragged board text")` | **변경(c182 목표)** |
| `'\n'` | `['']` → 폭 0 → ValueError | `['', '']` → 폭 0 → ValueError | 동일 |
| `'##\n\n'` | `['##', '']` → ragged | `['##', '', '']` → ragged | 동일 |
| `'#.\r\n'` | `'\r'` 문자 검사 → ValueError | 동일 | 동일 |
| 끝 개행 없는 정상 입력 (`board_to_text` 출력 포함) | 정상 변환 | 정상 변환 | 동일 |

- `text.split("\n")`은 항상 원소를 1개 이상 반환하므로 `lines[0]` 접근에서 IndexError가 나지 않습니다.

**초안 지적 사항 (최종본에 반영)**
1. 위험 등급이 역할마다 달랐습니다(P0/P1). 실제 테스트 실패이자 명세 위반이므로 **P1(정확성)**으로 통일했습니다.
2. BUG_HUNTER의 "`'##\n\n'`도 같은 경로를 탄다"는 부정확합니다. 이 입력은 수정 전에도 ValueError였으므로 실패 경로가 아닙니다.
3. PARTNER 초안은 다른 함수의 기존 `수정(리뷰)` 주석까지 지웠습니다. 동작 영향은 없지만 불필요한 변경이므로 원문을 유지했습니다.
4. "188/188 통과"는 어느 초안도 실행으로 확인하지 않았습니다. **미확인**으로 표시합니다.

**요청 점검 항목**
- 메모리: 모든 함수가 새 리스트를 반환하고 행 별칭이 없습니다.
- 동시성: `GameState`는 스레드 안전하지 않으며, 이 점이 주석에 명시되어 있습니다.
- 예외: `record_clear`는 append 성공 후 상태를 한꺼번에 반영합니다. `drop_row`에는 빈 조각 무한 루프 가드가 있습니다.
- 리소스: 파일·소켓·락 같은 해제 대상이 없습니다.
- 위 항목에서 추가로 고칠 결함은 없습니다.
- LangChain/LangGraph를 사용하지 않으므로 PROMPT_ENGINEER 설계 검토는 해당 없음입니다.

## 2. 위험도 및 진단 리포트

| # | 등급 | 위치 | 근거 | 조치 | 상태 |
|---|---|---|---|---|---|
| 1 | P1 | `text_to_board`의 끝 개행 `pop` 분기 | c182: `'#.\n'` → `[[1, 0]]`, 기대값 ValueError. 역변환·ragged 명세 위반 | **수정함(실행 코드)**: 분기 2줄 삭제 | 정적 확인. 실행 결과는 미확인 |
| 2 | 위험(미확인) | `text_to_board` 회귀 | `'##\n##\n'`처럼 끝 개행이 있는 다중 행 입력도 이제 거부됩니다. 이를 허용한다고 가정한 통과 테스트가 있으면 회귀가 생깁니다. c182와 모순되는 기대값이므로 존재 가능성은 낮다고 판단합니다 | 테스트 재실행으로 확인 | 미확인 |
| 3 | P2 | `column_heights` / `max_height` / `count_holes` | 빈 보드 `[]`에서 `board[0]` IndexError. 생성 함수들은 빈 보드를 만들지 않으며 명세에 정의가 없음 | 수정 불필요(통과 동작 보존) | — |
| 4 | P2 | `level_for_lines` / `combo_bonus` / `gravity_frames` | 비정수·bool 검증이 없음. 명세에 요구가 없음 | 수정 불필요 | — |
| 5 | 정보 | `GameState` 동시성 | read-modify-write 경쟁이 가능하나 주석에 호출 측 동기화 책임이 고지됨 | 수정 불필요 | — |
| 6 | 정보 | `drop_row`, `record_clear`, `GameState.__init__` | 무한 루프 가드, 원자적 상태 반영, None 센티널이 이미 적용됨 | 유지 | — |

**재현 (#1)**
- 호출: `text_to_board('#.\n')`
- 수정 전: `[[1, 0]]`
- 수정 후: `lines = ['#.', '']`이 되고, 두 번째 줄 길이 0 ≠ 폭 2이므로 `ValueError("ragged board text")`가 발생합니다.

**확인 필요:** `harness/tests/selffix_hard/` bench를 다시 실행해 188/188이 나오는지 확인해야 합니다.

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 테트리스 엔진(화면 없음) (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

보드는 rows x cols 리스트(0=빈칸, 1=블록), 조각은 0/1 2차원 리스트. top은 행, left는 열(0부터).
각 함수의 docstring이 명세다. 입력 보드·조각은 바꾸지 않고 새 객체를 돌려준다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import numbers
import random

# 표준 테트로미노 모양(#=블록, .=빈칸, 위 행부터):
#   I: ####   O: ##/##   T: ###/.#.   S: .##/##.   Z: ##./.##   J: #../###   L: ..#/###
# 수정: T·S·L 모양을 위 주석(명세)과 일치시킴. Z·J는 원래 정확해 그대로 둠.
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
# 수정: 4줄 점수 1000 -> 1200(명세 값).
LINE_SCORES = [0, 40, 100, 300, 1200]
# 레벨당 줄 수. 수정: 8 -> 10(level_for_lines/lines_to_next_level 명세 "10줄마다").
LINES_PER_LEVEL = 10


# ---------------------------------------------------------------- 보드
def new_board(rows=20, cols=10):
    """빈 보드. rows·cols는 1 이상 정수, 아니면 ValueError."""
    # 예외: bool·비정수·1 미만이면 ValueError(bool은 int 하위형이라 명시적으로 제외).
    for value in (rows, cols):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("rows and cols must be positive integers")
    # 주의: [[0]*cols]*rows는 모든 행이 같은 객체를 공유하므로 행마다 새로 만든다.
    return [[0] * cols for _ in range(rows)]


def copy_board(board):
    """행까지 새로 만든 복사본."""
    # 행 리스트까지 새로 생성해 원본 보드와의 별칭을 끊는다.
    return [list(row) for row in board]


def board_to_text(board):
    """블록은 '#', 빈칸은 '.'으로 위 행부터 한 줄씩, 줄 사이는 '\\n'."""
    # 인덱스 0 = 맨 위 행. 줄 구분은 '\n'(끝 개행 없음).
    return "\n".join("".join("#" if cell else "." for cell in row) for row in board)


def text_to_board(text):
    """board_to_text의 역변환(첫 줄이 맨 위 행, 칸은 int 0/1). 빈 문자열, 길이가 다른 줄, '#'/'.' 이외 문자는 ValueError."""
    # 예외: 빈 문자열, 0폭 줄, 길이가 다른 줄(끝 개행으로 생긴 빈 줄 포함), 허용되지 않은 문자 -> ValueError.
    if not text:
        raise ValueError("empty text")
    # 수정(리뷰): splitlines()는 '\r'·'\x0b'·'\x0c'·'\u2028' 등도 줄 구분자로 삼아
    # '#'/'.' 이외 문자를 조용히 통과시켰다. board_to_text의 구분자인 '\n'으로만 나눠
    # 나머지 문자는 아래 문자 검사에서 ValueError가 나게 한다.
    lines = text.split("\n")
    # 수정(리뷰 round2, 테스트 c182): 끝 개행 하나를 잘라내던 분기(lines.pop())를 제거했다.
    # board_to_text는 끝 개행을 만들지 않으므로 역변환 계약상 '#.\n'의 빈 끝 줄은 "길이가 다른 줄"이며
    # 아래 ragged 검사에서 ValueError가 된다.
    # 주의: '\n' 단독(첫 줄 폭 0)·'##\n\n'(ragged)·'\r' 포함 입력은 기존과 같이 ValueError.
    width = len(lines[0])
    if width == 0:
        # 0폭 보드는 new_board 계약(cols >= 1)과 맞지 않아 거부한다.
        raise ValueError("empty board line")
    board = []
    for line in lines:
        if len(line) != width:
            raise ValueError("ragged board text")
        if any(ch not in "#." for ch in line):
            raise ValueError("invalid board character")
        # 첫 줄이 맨 위 행이므로 순서대로 append, 칸은 int 0/1.
        board.append([1 if ch == "#" else 0 for ch in line])
    return board


# ---------------------------------------------------------------- 조각
def rotate_cw(piece):
    """시계 방향 90도: 위쪽 행이 오른쪽 열이 된다."""
    # 행 순서를 뒤집은 뒤 전치하면 시계 방향 회전(새 리스트 반환).
    return [list(row) for row in zip(*piece[::-1])]


def rotate_ccw(piece):
    """반시계 방향 90도: 위쪽 행이 왼쪽 열이 된다(뒤집힌 순서)."""
    # 전치한 뒤 행 순서를 뒤집으면 반시계 방향 회전(새 리스트 반환).
    return [list(row) for row in zip(*piece)][::-1]


def rotate_180(piece):
    """180도: 행 순서와 각 행의 칸 순서를 모두 뒤집는다."""
    # 행 순서와 칸 순서를 모두 뒤집는다(슬라이스로 새 리스트, 입력 보존).
    return [row[::-1] for row in piece[::-1]]


def piece_cells(piece):
    """블록 칸의 (행, 열) 목록(행 우선, 왼쪽부터)."""
    # (r, c) 순서. 원래 (c, r)로 뒤바뀌어 있었음.
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
    # max는 포함 경계이므로 슬라이스 끝은 +1. list()로 새 행을 만들어 입력과 분리한다.
    return [list(row[left:right + 1]) for row in piece[top:bottom + 1]]


def piece_size(piece):
    """(높이, 너비)."""
    # (행 수, 첫 행의 칸 수). 빈 조각이면 너비 0.
    return len(piece), (len(piece[0]) if piece else 0)


# ---------------------------------------------------------------- 놓기·지우기
def can_place(board, piece, top, left):
    """조각의 블록 칸이 모두 보드 안이고 기존 블록과 겹치지 않으면 True(빈칸은 밖에 있어도 된다)."""
    rows = len(board)
    cols = len(board[0]) if board else 0
    for r, c in piece_cells(piece):
        y, x = top + r, left + c
        # 경계: 0 <= y < rows, 0 <= x < cols(원래 -1·> 비교로 랩어라운드·IndexError 가능).
        if y < 0 or y >= rows or x < 0 or x >= cols:
            return False
        # 기존 블록과 겹치면 불가(원래 판정이 반대였음).
        if board[y][x]:
            return False
    return True


def place(board, piece, top, left):
    """조각을 놓은 새 보드. 놓을 수 없으면 ValueError. 조각의 빈칸은 기존 블록을 지우지 않는다."""
    # 입력 보드를 바꾸지 않도록 복사본에 기록한다.
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
    # 남긴 행과 새 빈 행 모두 새 리스트(별칭 방지).
    cols = len(board[0]) if board else 0
    kept = [list(row) for row in board if not all(row)]
    cleared = len(board) - len(kept)
    return [[0] * cols for _ in range(cleared)] + kept, cleared


def drop_row(board, piece, left, top=0):
    """top(기본 0 = 맨 위 행)에서 아래로 떨어뜨렸을 때 멈추는 행. 시작 위치에 놓을 수 없으면 ValueError."""
    # 수정(리뷰): 블록이 없는 조각은 can_place가 어떤 위치에서도 True라 아래 while이 끝나지 않는다
    # (무한 루프·CPU 점유). 멈출 행이 정의되지 않으므로 trim_piece와 같은 계약으로 ValueError.
    # hard_drop도 이 경로를 거치므로 함께 보호된다.
    if not piece_cells(piece):
        raise ValueError("piece has no blocks")
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed at the start position")
    # 아래 칸이 막힐 때까지 반복(원래는 한 칸만 이동). 블록이 있으면 보드 높이 안에서 반드시 멈춘다.
    while can_place(board, piece, top + 1, left):
        top += 1
    return top


def hard_drop(board, piece, left, top=0):
    """top(기본 0)에서 끝까지 떨어뜨려 놓은 뒤 줄을 지운 튜플 (새 보드, 떨어진 칸 수, 지운 행 수)."""
    # 순서: 착지 행 계산 -> 놓기 -> 줄 지우기(원래는 놓기 전에 지웠음).
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
    heights = []
    for x in range(len(board[0])):
        height = 0
        for y in range(rows):
            if board[y][x]:  # 원래 board[x][y]로 인덱스가 뒤바뀌어 있었음.
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
    cleared가 0~4가 아니거나 level이 음수면 ValueError."""
    # 수정(리뷰): 1.5 같은 비정수는 범위 비교를 통과한 뒤 LINE_SCORES[1.5]에서 TypeError가 났고,
    # True는 1로 취급돼 점수가 나왔다. 명세("0~4가 아니면 ValueError")에 맞춰 bool·비정수도 거부한다.
    # 주의: numbers.Integral로 검사해 numpy 정수 등 정수 타입은 계속 허용한다(bool 제외는 new_board와 같은 규칙).
    if (isinstance(cleared, bool) or not isinstance(cleared, numbers.Integral)
            or cleared < 0 or cleared > 4):
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
    """7-bag 순서: 조각 이름('I','O','T','S','Z','J','L' 문자열) 7종을 이름순으로 한 묶음씩 random.Random(seed)로 섞어
    이어 붙인 앞 count개(seed가 같으면 같은 순서). count < 0이면 ValueError."""
    if count < 0:
        raise ValueError("count must not be negative")
    # seed로 만든 지역 RNG(재현성 확보, 전역 random 상태 오염 없음).
    rng = random.Random(seed)
    sequence = []
    while len(sequence) < count:
        bag = sorted(PIECES)  # 조각 모양이 아닌 이름 문자열을 이름순으로.
        rng.shuffle(bag)
        sequence.extend(bag)
    return sequence[:count]


# ---------------------------------------------------------------- 게임 상태
class GameState:
    """점수·줄 수·콤보·보관(hold)을 관리한다. 인스턴스마다 상태를 따로 가진다."""

    # 주의: 스레드 안전하지 않음. 여러 스레드가 한 인스턴스를 공유하면 호출 측에서 동기화해야 한다.

    def __init__(self, level=0, log=None):
        # 초기 상태: 점수·줄 수·콤보 0, 시작 레벨 = level, 보관 조각 없음(None), 보관 가능, 기록은 빈 목록.
        # log=[] 가변 기본 인자는 모든 인스턴스가 공유하므로 None 센티널로 인스턴스마다 새 목록을 만든다.
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
        # 반영 전 레벨로 계산. score_for_lines의 ValueError가 상태 변경 전에 나도록 먼저 호출한다.
        level = self.level
        gained = score_for_lines(cleared, level)
        # 수정(리뷰): 기존에는 combo·lines·score·can_hold를 바꾼 뒤 log.append를 해서,
        # 주입된 log가 append에 실패하면 상태가 일부만 반영된 채 남았다.
        # 새 combo는 지역 변수로 계산하고, 실패할 수 있는 append가 성공한 뒤에 상태를 한꺼번에 반영한다.
        if cleared > 0:
            combo = self.combo + 1
            # 첫 클리어(combo=1)는 combo_bonus(0)=0이라 2번째 연속부터 보너스가 붙는다.
            gained += combo_bonus(combo - 1, level)
        else:
            combo = 0
        self.log.append((cleared, gained))
        self.combo = combo
        self.lines += cleared
        self.score += gained
        self.can_hold = True
        return gained

    def hold(self, current):
        """현재 조각 이름을 보관하고 이전 보관 조각(없으면 None)을 돌려준다.
        한 번 놓기 전에 두 번 보관하면 ValueError."""
        if not self.can_hold:
            raise ValueError("cannot hold twice before placing a piece")
        previous, self.held = self.held, current
        self.can_hold = False
        return previous
```

**변경 요약**
- 실행 코드 변경은 `text_to_board`에서 끝 개행 `pop` 분기 2줄을 삭제한 것뿐이며, 관련 주석도 새 계약에 맞게 정정했습니다.
- 나머지 함수와 기존 주석은 입력 소스와 동일합니다.
- 정적 추적상 c182는 통과하고, 끝 개행이 없는 입력의 동작은 바뀌지 않습니다.
- 188/188 통과는 bench 재실행 전까지 **미확인**입니다.