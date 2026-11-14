"""테트리스 핵심 로직 자가 수정 채점용 테스트 100건 (2026-11-10, LuckyBoys 요청: AI 4종 비교).

목적
- AI(Gemini·ChatGPT·Claude·Ollama)가 만든 tetris_core.py 제안 소스를 같은 100건으로 채점한다.
- 기준은 원본 tetris_core.py의 docstring(명세)이다. 원본에 일부러 넣은 결함
  (rotate가 전치만 함, clear_lines가 빈 줄을 채우지 않음)은 여기서 실패로 드러나야 한다.

구성(합계 100)
- new_board 17 (정상 10 + 잘못된 크기 ValueError 6 + 기본값 1)
- rotate 20 (테트로미노 7종 시계 방향 7 + 4번 회전=원래 7 + 직사각형 숫자판 3 + 입력 불변 1 + 1x1 1 + 180도 1)
- can_place 25 (안쪽 8 + 경계 밖 8 + 충돌 4 + 맞닿음 2 + 빈칸이 블록 위 2 + 빈칸이 보드 밖 1)
- place 15 (칸 설정 5 + 원본 불변 3 + 경계 밖 ValueError 3 + 충돌 ValueError 2 + 새 객체 1 + 기존 블록 유지 1)
- clear_lines 23 (데이터 18 + 원본 불변 1 + 행 객체 독립 1 + 높이 유지 3)

주의
- 파일 이름이 test_로 시작하지 않아 전체 회귀에 섞이지 않는다(채점 스크립트가 직접 실행).
- 시계 방향 기준: 위쪽 행이 오른쪽 열이 된다. 참조 구현 _ref_rotate는 zip(*piece[::-1]).
"""
import copy

import pytest

from FastAPI.LangGraph.selffix_demo import tetris_core as tc

# 표준 테트로미노 7종(0=빈칸, 1=블록)
PIECES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[1, 1, 1], [0, 1, 0]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}
I_VERTICAL = [[1], [1], [1], [1]]


def _ref_rotate(piece):
    """참조 시계 방향 90도 회전: 행 순서를 뒤집은 뒤 전치한다."""
    return [list(row) for row in zip(*piece[::-1])]


def _board(rows=4, cols=4, filled=()):
    """테스트용 보드를 만든다(filled: 블록이 있는 (y, x) 좌표들). 테스트 대상 함수에 의존하지 않는다."""
    board = [[0] * cols for _ in range(rows)]
    for y, x in filled:
        board[y][x] = 1
    return board


def _cells(board):
    """보드에서 블록이 있는 (y, x) 좌표 집합."""
    return {(y, x) for y, row in enumerate(board) for x, cell in enumerate(row) if cell}


# ---------------- new_board 17건 ----------------
@pytest.mark.parametrize("rows,cols", [(1, 1), (20, 10), (4, 4), (2, 3), (3, 2),
                                       (1, 10), (10, 1), (5, 7), (22, 10), (8, 8)])
def test_new_board_shape(rows, cols):
    """크기가 맞고, 모두 빈칸이며, 행끼리 같은 객체를 공유하지 않는다."""
    board = tc.new_board(rows, cols)
    assert len(board) == rows and all(len(row) == cols for row in board)
    assert all(cell == 0 for row in board for cell in row)
    board[0][0] = 1  # 한 행을 바꿔도 다른 행은 그대로여야 한다([[0]*c]*r 실수 검출)
    assert all(row[0] == 0 for row in board[1:])


@pytest.mark.parametrize("rows,cols", [(0, 10), (10, 0), (-1, 5), (5, -1), (0, 0), (-3, -3)])
def test_new_board_invalid_value_error(rows, cols):
    """rows·cols가 1보다 작으면 ValueError."""
    with pytest.raises(ValueError):
        tc.new_board(rows, cols)


def test_new_board_default_20x10():
    """기본값은 20행 x 10열."""
    board = tc.new_board()
    assert len(board) == 20 and all(len(row) == 10 for row in board)


# ---------------- rotate 20건 ----------------
@pytest.mark.parametrize("name", list(PIECES))
def test_rotate_clockwise_tetromino(name):
    """테트로미노 7종을 시계 방향 90도로 돌린 결과가 참조 구현과 같다."""
    assert tc.rotate(PIECES[name]) == _ref_rotate(PIECES[name])


@pytest.mark.parametrize("name", list(PIECES))
def test_rotate_four_times_identity(name):
    """네 번 돌리면 원래 모양으로 돌아온다."""
    piece = PIECES[name]
    result = piece
    for _ in range(4):
        result = tc.rotate(result)
    assert result == piece


@pytest.mark.parametrize("piece,expected", [
    ([[1, 2, 3], [4, 5, 6]], [[4, 1], [5, 2], [6, 3]]),
    ([[1, 2], [3, 4], [5, 6]], [[5, 3, 1], [6, 4, 2]]),
    ([[1, 2], [3, 4]], [[3, 1], [4, 2]]),
])
def test_rotate_numbered_grid(piece, expected):
    """칸마다 다른 숫자를 넣어 전치(대각선 뒤집기)와 시계 방향 회전을 구별한다."""
    assert tc.rotate(piece) == expected


def test_rotate_does_not_mutate_input():
    """rotate는 입력 조각을 바꾸지 않는다."""
    piece = copy.deepcopy(PIECES["L"])
    tc.rotate(piece)
    assert piece == PIECES["L"]


def test_rotate_single_cell():
    """1x1 조각은 그대로다."""
    assert tc.rotate([[1]]) == [[1]]


def test_rotate_twice_is_180_degrees():
    """두 번 돌리면 180도: 행 순서와 각 행의 칸 순서가 모두 뒤집힌다."""
    piece = [[1, 2, 3], [4, 5, 6]]
    assert tc.rotate(tc.rotate(piece)) == [[6, 5, 4], [3, 2, 1]]


# ---------------- can_place 25건 (4x4 보드) ----------------
CAN_PLACE_CASES = [
    # 안쪽(True) 8건
    ("inside_O_00", (), PIECES["O"], 0, 0, True),
    ("inside_O_22", (), PIECES["O"], 2, 2, True),
    ("inside_I_row3", (), PIECES["I"], 3, 0, True),
    ("inside_Ivert_col3", (), I_VERTICAL, 0, 3, True),
    ("inside_T_21", (), PIECES["T"], 2, 1, True),
    ("inside_dot_33", (), [[1]], 3, 3, True),
    ("inside_S_01", (), PIECES["S"], 0, 1, True),
    ("inside_L_10", (), PIECES["L"], 1, 0, True),
    # 경계 밖(False) 8건
    ("out_bottom_O", (), PIECES["O"], 3, 0, False),
    ("out_right_O", (), PIECES["O"], 0, 3, False),
    ("out_top_O", (), PIECES["O"], -1, 0, False),
    ("out_left_O", (), PIECES["O"], 0, -1, False),
    ("out_right_I", (), PIECES["I"], 0, 1, False),
    ("out_bottom_Ivert", (), I_VERTICAL, 1, 0, False),
    ("out_bottom_dot", (), [[1]], 4, 0, False),
    ("out_right_dot", (), [[1]], 0, 4, False),
    # 충돌(False) 4건
    ("hit_O_corner", ((0, 0),), PIECES["O"], 0, 0, False),
    ("hit_O_inner", ((1, 1),), PIECES["O"], 0, 0, False),
    ("hit_dot", ((3, 3),), [[1]], 3, 3, False),
    ("hit_I_row2", ((2, 0),), PIECES["I"], 2, 0, False),
    # 맞닿음(True) 2건: 옆·아래에 블록이 있어도 겹치지 않으면 놓을 수 있다
    ("touch_side", ((0, 2),), PIECES["O"], 0, 0, True),
    ("touch_floor", ((3, 0), (3, 1), (3, 2), (3, 3)), PIECES["O"], 1, 0, True),
    # 조각의 빈칸이 블록 위에 있어도 True 2건
    ("gap_T_over_block", ((1, 0),), PIECES["T"], 0, 0, True),
    ("gap_S_over_block", ((0, 0),), PIECES["S"], 0, 0, True),
    # 조각의 빈칸이 보드 밖에 있어도 True 1건
    ("gap_outside_left", (), [[0, 1]], 0, -1, True),
]


@pytest.mark.parametrize("case,filled,piece,top,left,expected", CAN_PLACE_CASES,
                         ids=[c[0] for c in CAN_PLACE_CASES])
def test_can_place(case, filled, piece, top, left, expected):
    """보드 안이고 기존 블록과 겹치지 않을 때만 True(빈칸 0은 검사하지 않는다)."""
    assert tc.can_place(_board(filled=filled), piece, top, left) is expected


# ---------------- place 15건 (4x4 보드) ----------------
PLACE_CELL_CASES = [
    ("O_00", (), PIECES["O"], 0, 0, {(0, 0), (0, 1), (1, 0), (1, 1)}),
    ("I_30", (), PIECES["I"], 3, 0, {(3, 0), (3, 1), (3, 2), (3, 3)}),
    ("T_21", (), PIECES["T"], 2, 1, {(2, 1), (2, 2), (2, 3), (3, 2)}),
    ("dot_12", (), [[1]], 1, 2, {(1, 2)}),
    ("S_01_keep33", ((3, 3),), PIECES["S"], 0, 1, {(0, 2), (0, 3), (1, 1), (1, 2), (3, 3)}),
]


@pytest.mark.parametrize("case,filled,piece,top,left,expected", PLACE_CELL_CASES,
                         ids=[c[0] for c in PLACE_CELL_CASES])
def test_place_sets_cells(case, filled, piece, top, left, expected):
    """놓은 뒤 블록 좌표가 정확히 기대 집합과 같다(기존 블록 포함)."""
    assert _cells(tc.place(_board(filled=filled), piece, top, left)) == expected


@pytest.mark.parametrize("filled,piece,top,left", [
    ((), PIECES["O"], 0, 0),
    (((3, 3),), PIECES["T"], 0, 0),
    ((), PIECES["I"], 2, 0),
])
def test_place_does_not_mutate_board(filled, piece, top, left):
    """원래 보드는 바꾸지 않는다."""
    board = _board(filled=filled)
    snapshot = copy.deepcopy(board)
    tc.place(board, piece, top, left)
    assert board == snapshot


@pytest.mark.parametrize("piece,top,left", [(PIECES["O"], 3, 3), (PIECES["I"], 0, 1), ([[1]], -1, 0)])
def test_place_out_of_bounds_value_error(piece, top, left):
    """보드 밖이면 ValueError."""
    with pytest.raises(ValueError):
        tc.place(_board(), piece, top, left)


@pytest.mark.parametrize("filled,piece,top,left", [(((0, 0),), PIECES["O"], 0, 0),
                                                    (((2, 2),), PIECES["T"], 2, 1)])
def test_place_collision_value_error(filled, piece, top, left):
    """기존 블록과 겹치면 ValueError."""
    with pytest.raises(ValueError):
        tc.place(_board(filled=filled), piece, top, left)


def test_place_returns_new_objects():
    """결과 보드와 그 행들은 원래 보드와 다른 객체다."""
    board = _board()
    result = tc.place(board, [[1]], 0, 0)
    assert result is not board and all(r is not b for r, b in zip(result, board))


def test_place_gap_keeps_existing_block():
    """조각의 빈칸(0)이 기존 블록을 지우지 않는다."""
    result = tc.place(_board(filled=((1, 0),)), PIECES["T"], 0, 0)
    assert _cells(result) == {(0, 0), (0, 1), (0, 2), (1, 1), (1, 0)}


# ---------------- clear_lines 23건 ----------------
CLEAR_CASES = [
    ("empty_2x2", [[0, 0], [0, 0]], [[0, 0], [0, 0]], 0),
    ("partial_bottom", [[0, 0], [1, 0]], [[0, 0], [1, 0]], 0),
    ("diagonal", [[1, 0], [0, 1]], [[1, 0], [0, 1]], 0),
    ("bottom_full", [[0, 0], [1, 1]], [[0, 0], [0, 0]], 1),
    ("bottom_full_above_block", [[1, 0], [1, 1]], [[0, 0], [1, 0]], 1),
    ("all_full_2x2", [[1, 1], [1, 1]], [[0, 0], [0, 0]], 2),
    ("middle_full", [[1, 0, 0], [1, 1, 1], [0, 1, 0]], [[0, 0, 0], [1, 0, 0], [0, 1, 0]], 1),
    ("top_and_bottom_full", [[1, 1, 1], [0, 1, 0], [1, 1, 1]], [[0, 0, 0], [0, 0, 0], [0, 1, 0]], 2),
    ("two_bottom_full", [[0, 1, 0], [1, 1, 1], [1, 1, 1]], [[0, 0, 0], [0, 0, 0], [0, 1, 0]], 2),
    ("all_full_3x3", [[1] * 3 for _ in range(3)], [[0] * 3 for _ in range(3)], 3),
    ("single_row_full", [[1, 1, 1, 1]], [[0, 0, 0, 0]], 1),
    ("single_row_not_full", [[1, 0, 1, 1]], [[1, 0, 1, 1]], 0),
    ("4x4_two_bottom", [[0, 0, 0, 0], [1, 0, 0, 0], [1, 1, 1, 1], [1, 1, 1, 1]],
     [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [1, 0, 0, 0]], 2),
    ("single_column", [[1], [0], [1]], [[0], [0], [0]], 2),
    ("single_column_all_full", [[1], [1]], [[0], [0]], 2),
    ("4x2_alternating", [[1, 0], [1, 1], [0, 1], [1, 1]], [[0, 0], [0, 0], [1, 0], [0, 1]], 2),
    ("top_row_full_only", [[1, 1], [0, 1], [1, 0]], [[0, 0], [0, 1], [1, 0]], 1),
    ("5x3_mixed", [[0, 0, 1], [1, 1, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
     [[0, 0, 0], [0, 0, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1]], 2),
]


@pytest.mark.parametrize("case,board,expected_board,expected_count", CLEAR_CASES,
                         ids=[c[0] for c in CLEAR_CASES])
def test_clear_lines_result(case, board, expected_board, expected_count):
    """가득 찬 줄을 지우고 위에 빈 줄을 채운 보드와 지운 줄 수를 돌려준다(높이 유지)."""
    new_board, count = tc.clear_lines(board)
    assert count == expected_count
    assert new_board == expected_board


def test_clear_lines_does_not_mutate_input():
    """원래 보드는 바꾸지 않는다."""
    board = [[0, 1], [1, 1]]
    snapshot = copy.deepcopy(board)
    tc.clear_lines(board)
    assert board == snapshot


def test_clear_lines_rows_are_independent():
    """채운 빈 줄끼리 같은 리스트 객체를 공유하지 않는다([[0]*c]*n 실수 검출)."""
    new_board, _ = tc.clear_lines([[1, 1], [1, 1], [0, 1]])
    new_board[0][0] = 1
    assert new_board[1][0] == 0


@pytest.mark.parametrize("rows,cols", [(2, 2), (20, 10), (1, 5)])
def test_clear_lines_keeps_height(rows, cols):
    """맨 아래 줄이 가득 차도 보드 높이·너비는 그대로다."""
    board = [[0] * cols for _ in range(rows - 1)] + [[1] * cols]
    new_board, count = tc.clear_lines(board)
    assert count == 1
    assert len(new_board) == rows and all(len(row) == cols for row in new_board)
