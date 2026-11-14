## 1. 전문가적 견해 및 종합 평가

**결론: 실행 코드 4곳을 수정해야 합니다.** 그중 무한 루프 1건은 즉시 고쳐야 할 결함입니다. 메모리 별칭, 리소스 해제, 전역 RNG 오염 문제는 없습니다. 동시성은 클래스 주석에 "호출 측 동기화"로 계약이 명시되어 있어 수정 대상이 아닙니다.

**검증 방식과 한계**
- 정적 분석과 손 추적만 했습니다. 코드를 실행하지 않았고 `harness/tests/selffix_hard/` bench 파일도 보지 못했습니다. 아래 판정은 모두 **실행 검증 전(미확인)** 상태입니다.
- 소스에 LangChain/LangGraph import나 사용이 없습니다. 경로 이름에만 나옵니다. 그래서 PROMPT_ENGINEER 설계 검토는 **해당 없음**입니다.

**초안 검증 결과.** 초안 4개 역할(PROMPT_ENGINEER·REVIEWER·BUG_HUNTER·PARTNER)의 주장을 소스와 대조했습니다.

| 초안 주장 | 판정 | 근거 |
|---|---|---|
| `drop_row`에 블록 없는 조각을 넣으면 무한 루프 (PE·REVIEWER) | **채택** | `piece_cells`가 비면 `can_place`가 항상 True입니다. 그래서 `while`이 끝나지 않습니다. PARTNER는 이 결함을 놓쳤습니다. |
| `text_to_board`의 `splitlines()`가 명세 위반 (PE·REVIEWER) | **채택, 수정 방식은 변경** | `"##\r##"`, `"##\x0c##"` 같은 입력이 통과합니다. 다만 초안의 `split("\n")` 단순 치환은 기존에 허용되던 끝 개행 하나(`"##\n"`)까지 거부합니다. 그래서 그 경우는 기존 동작을 유지하도록 고쳤습니다. |
| `score_for_lines(1.5, 0)`이 ValueError가 아닌 TypeError (REVIEWER·BUG_HUNTER) | **채택** | 범위 비교를 통과한 뒤 `LINE_SCORES[1.5]`에서 TypeError가 납니다. 초안의 `isinstance(int)` 검사는 numpy 정수를 거부하는 부작용이 있습니다. 그래서 `numbers.Integral`을 쓰고 bool만 제외했습니다. |
| `record_clear`는 `log.append`가 실패하면 상태가 일부만 바뀐 채 남음 (BUG_HUNTER) | **채택, 구현은 단순화** | 원본은 `combo/lines/score/can_hold`를 바꾼 뒤에 `append`합니다. 초안의 "변경 후 복구" 방식 대신, 새 combo를 지역 변수로 계산하고 `append`가 성공한 뒤 커밋합니다. 그 결과 PE·PARTNER의 "예외 원자성 양호" 평가는 부분적으로 틀린 것이 됩니다. |
| `lines_to_next_level` 음수면 ValueError 추가 (PARTNER) | **기각(보류)** | docstring에는 "1~10"만 있고 예외 조건이 없습니다. 음수를 넣어도 결과는 1~10 범위 안에 있습니다. 예외를 추가하면 명세에 없는 계약 변경이 됩니다. |
| "운영 지침상 전체 소스를 출력하지 않음" (PE·BUG_HUNTER) | **기각** | 사용자 요청과 충돌합니다. 아래 3번에 전체 소스를 넣었습니다. |
| 줄 번호 인용(L157 등)과 "L1–L345" (REVIEWER) | **신뢰 불가** | 실제 줄 수와 맞지 않습니다. 이 리포트에서는 함수 이름으로만 위치를 표시합니다. |
| 위험도 "중간(P0)" 표기 (REVIEWER) | **정정** | 등급 표기가 서로 모순됩니다. 아래 표에서 다시 매겼습니다. |

**이미 명세와 맞는 부분(변경 없음):** PIECES 모양, LINE_SCORES, LINES_PER_LEVEL, 회전 3종, `piece_cells`의 (r, c) 순서, `can_place` 경계, `hard_drop` 순서, `column_heights` 인덱스, `GameState`의 가변 기본 인자 처리.

## 2. 위험도 및 진단 리포트

### 수정 필요 (3번에서 실행 코드까지 수정함)

| # | 위험도 | 대상 | 진단 근거 | 수정 내용 |
|---|---|---|---|---|
| 1 | **높음 (행/DoS)** | `drop_row` (`hard_drop` 경유 포함) | `[[0, 0]]`이나 `[]`를 넣으면 `can_place`가 모든 위치에서 True를 반환합니다. 그래서 `top += 1`이 끝없이 반복되고 CPU를 계속 점유합니다. 착지 행은 정의되지 않습니다. | 시작 위치를 검사하기 전에 `piece_cells`가 비어 있으면 `ValueError("piece has no blocks")`를 냅니다. 메시지는 `trim_piece`와 같습니다. 블록이 하나라도 있으면 보드 높이 안에서 루프가 반드시 끝납니다. |
| 2 | 중간 (명세 위반) | `text_to_board` | `splitlines()`는 `\r`, `\x0b`, `\x0c`, `\x1c`~`\x1e`, `\x85`, `\u2028`, `\u2029`도 줄 구분자로 처리합니다. 그래서 '#'/'.' 이외 문자가 들어간 입력을 받아들입니다. `board_to_text`의 구분자는 `'\n'`뿐입니다. | `split("\n")`으로 나눕니다. 끝 개행 하나는 기존과 같이 허용합니다. `"\n"`, `"##\n\n"`, 빈 문자열의 결과는 기존과 같습니다. `"\r\n"` 입력은 이제 거부되며, 이것이 명세에 맞는 동작 변화입니다. |
| 3 | 중간 (예외 계약) | `score_for_lines` (`record_clear` 경유 포함) | `1.5`는 TypeError를 냅니다. `True`는 1로 취급되어 40점을 반환합니다. 명세는 "0~4가 아니면 ValueError"입니다. | bool이거나 `numbers.Integral`이 아니면 `ValueError`를 냅니다. numpy 정수 같은 Integral 등록 타입은 계속 허용합니다. |
| 4 | 낮음 (예외 원자성) | `GameState.record_clear` | `log`로 append할 수 없는 객체(예: `log=()`)를 주입하면 `combo/lines/score/can_hold`가 바뀐 뒤 예외가 납니다. 상태가 일부만 반영된 채 남습니다. | 새 combo와 `gained`를 지역 변수로 계산합니다. `log.append`가 성공한 뒤에 상태를 커밋합니다. 정상 경로의 반환값, 기록 내용, 최종 상태는 동일합니다. |

### 수정 불필요 (진단만, 코드 변경 없음)

| # | 구분 | 대상 | 진단 | 사유 |
|---|---|---|---|---|
| 5 | 동시성 | `GameState` | `record_clear`와 `hold`는 비원자적인 읽기-수정-쓰기입니다. | 클래스 주석에 호출 측 동기화가 계약으로 명시되어 있습니다. 모듈 함수는 모두 입력을 바꾸지 않습니다. |
| 6 | 메모리 | `GameState.log` | 조각을 놓을 때마다 무제한으로 쌓입니다. | 공개 속성이며 리스트 계약입니다. 상한을 두려면 설계 결정이 필요합니다. |
| 7 | 별칭 | `PIECES`, `GameState(log=외부리스트)` | 전역 가변 리스트가 노출되고, 주입한 log는 별칭으로 공유됩니다. | 엔진 내부는 이 객체들을 변경하지 않습니다. log 주입은 의도된 기능입니다. 튜플로 바꾸면 공개 타입이 달라집니다. |
| 8 | 입력 검증 | `lines_to_next_level(음수)` | 결과가 1~10 범위 안의 값입니다. | 명세에 예외 조건이 없습니다. 테스트 기대가 있는지는 **미확인**입니다. |
| 9 | 입력 검증 | `GameState(level<0)`, `gravity_frames(음수)` | 음수 레벨을 검증하지 않습니다. | 명세에 예외 조건이 없습니다. `record_clear`는 상태를 바꾸기 전에 거부합니다. |
| 10 | 예외 | `column_heights`, `count_holes`, `max_height`에 빈 보드 `[]` | IndexError 또는 ValueError가 납니다. | `new_board`와 `text_to_board`가 1×1 미만 보드를 만들지 않습니다. |
| 11 | 예외 | `bag_sequence(2.5, s)` | 슬라이스에서 TypeError가 납니다. | 명세는 `count < 0`만 정의합니다. |
| 12 | 리소스 | 모듈 전체 | 파일, 소켓, 락이 없습니다. `bag_sequence`는 지역 RNG를 씁니다. | 해제할 대상이 없습니다. |

### 권장 회귀 테스트 (미실행)
- `drop_row(new_board(), [[0, 0]], 0)`과 `hard_drop(new_board(), [], 0)`이 타임아웃(1초) 안에 `ValueError`를 내야 합니다.
- `text_to_board("##\r##")`와 `text_to_board("#.\x0c#.")`는 `ValueError`를 내야 합니다. `text_to_board("##\n")`은 `[[1, 1]]`이어야 하고, `board_to_text`와의 왕복 변환 결과가 같아야 합니다.
- `score_for_lines` 검사:
  - `1.5`, `True`, `5`, `-1`을 넣으면 `ValueError`가 나야 합니다.
  - `score_for_lines(4, 0) == 1200`, `score_for_lines(1, 2) == 120`이어야 합니다.
- `GameState(log=())` 검사: `record_clear(1)` 호출이 AttributeError로 실패한 뒤에도 `score`, `lines`, `combo`가 0이어야 합니다.
- 정상 경로에서 `record_clear(1)`을 두 번 호출하면 반환값은 40과 90이어야 하고, `log`는 `[(1, 40), (1, 90)]`이어야 합니다.
- 기존 bench 전체를 수정 전과 후에 각각 실행해 통과 수를 비교합니다(**미확인**).

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
    # 예외: 빈 문자열, 0폭 줄, 길이가 다른 줄, 허용되지 않은 문자 -> ValueError.
    if not text:
        raise ValueError("empty text")
    # 수정(리뷰): splitlines()는 '\r'·'\x0b'·'\x0c'·'\u2028' 등도 줄 구분자로 삼아
    # '#'/'.' 이외 문자를 조용히 통과시켰다. board_to_text의 구분자인 '\n'으로만 나눠
    # 나머지 문자는 아래 문자 검사에서 ValueError가 나게 한다.
    lines = text.split("\n")
    # 주의: 기존(splitlines)과 같이 끝 개행 하나는 허용한다("##\n" -> 1행). "\n"·"##\n\n" 결과도 기존과 같다.
    if len(lines) > 1 and lines[-1] == "":
        lines.pop()
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

**미확인 사항 요약**
- 실행과 bench 통과 여부를 확인하지 않았습니다.
- 테스트가 `"\r\n"` 입력이나 `True`를 `cleared`로 쓰는 경우를 기대하는지 모릅니다.
- `lines_to_next_level(음수)`에 대한 테스트 기대가 있는지 모릅니다.

위 회귀 테스트로 확인한 뒤 완료로 판정하시기 바랍니다.