"""시연용 테트리스 핵심 로직 테스트 — 자동 수정 후 이 테스트가 통과해야 수정이 유지된다 (2026-11-10)."""
import pytest

from FastAPI.LangGraph.selffix_demo import tetris_core as t


def test_rotate_clockwise():
    # L 모양: 시계 방향 90도 회전 결과
    piece = [[1, 0],
             [1, 0],
             [1, 1]]
    assert t.rotate(piece) == [[1, 1, 1],
                               [1, 0, 0]]


def test_place_and_collision():
    board = t.new_board(4, 4)
    board = t.place(board, [[1, 1]], 3, 0)
    assert board[3][:2] == [1, 1]
    assert not t.can_place(board, [[1]], 3, 0)   # 겹침
    assert not t.can_place(board, [[1, 1]], 0, 3)  # 오른쪽 밖


def test_clear_lines_keeps_board_height():
    board = [[0, 0, 0],
             [1, 1, 1],
             [1, 0, 1]]
    new, cleared = t.clear_lines(board)
    assert cleared == 1
    assert new == [[0, 0, 0],
                   [0, 0, 0],
                   [1, 0, 1]]


@pytest.mark.parametrize("rows,cols", [(0, 10), (20, 0), (-1, 5)])
def test_bad_board_size_rejected(rows, cols):
    """잘못된 입력: 0 또는 음수 크기."""
    with pytest.raises(ValueError):
        t.new_board(rows, cols)
