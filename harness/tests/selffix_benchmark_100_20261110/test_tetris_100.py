"""100개 독립 입력으로 테트리스 핵심 규칙과 경계 조건을 검증한다.

경로 안내: tetris_core.py는 이 파일과 같은 폴더의 격리 복사본이다.
이 테스트 모듈은 운영 원본을 import하지 않으며, AI가 주석과 import를 따라
수정 대상을 찾아낼 수 있는지 확인한다.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


# 이 import 경로가 가리키는 격리 테트리스 코어만 로드한다.
_SOURCE = Path(__file__).with_name("tetris_core.py")
_SPEC = spec_from_file_location("selffix_benchmark_tetris", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
tetris = module_from_spec(_SPEC)
_SPEC.loader.exec_module(tetris)


def _reference_rotate(piece):
    """검증 대상 구현과 분리된 인덱스 순회로 시계 방향 회전 기대값을 만든다."""
    rows = len(piece)
    cols = len(piece[0])
    return [[piece[rows - 1 - r][c] for r in range(rows)] for c in range(cols)]


def _build_cases():
    """40 회전, 15 보드 생성, 20 배치 가능성, 10 놓기, 15 줄 삭제 사례를 만든다."""
    cases = []
    # 다양한 직사각형과 비대칭 조각으로 전치와 시계 방향 회전을 구분한다.
    rotations = []
    for rows in range(1, 6):
        for cols in range(1, 6):
            piece = [
                [int(((r + 1) * (c + 3) + rows * 2 + cols) % 4 in (0, 1)) for c in range(cols)]
                for r in range(rows)
            ]
            if not any(any(row) for row in piece):
                piece[0][0] = 1
            rotations.append(piece)
    for seed in range(15):
        rows = 2 + seed % 4
        cols = 2 + (seed * 3) % 5
        piece = [
            [int((r * 7 + c * 11 + seed * 3) % 5 < 2) for c in range(cols)]
            for r in range(rows)
        ]
        if not any(any(row) for row in piece):
            piece[-1][-1] = 1
        rotations.append(piece)
    for index, piece in enumerate(rotations, 1):
        cases.append((f"rotate_{index:02d}", "rotate", piece, _reference_rotate(piece)))

    # 정상 크기 15종에서 모양과 초기값을 검증한다.
    sizes = [(1, 1), (1, 2), (2, 1), (2, 2), (3, 4), (4, 3), (5, 5), (6, 2),
             (2, 6), (7, 8), (8, 7), (9, 10), (10, 9), (20, 1), (1, 20)]
    for index, size in enumerate(sizes, 1):
        cases.append((f"new_board_{index:02d}", "new_board", size, None))

    # 10개 허용 위치와 10개 충돌·경계 초과 위치를 확인한다.
    for index, (row, col) in enumerate([(0, 0), (0, 4), (4, 0), (4, 4), (1, 2),
                                         (2, 1), (3, 3), (1, 4), (4, 2), (2, 3)], 1):
        board = [[0] * 5 for _ in range(5)]
        cases.append((f"can_place_valid_{index:02d}", "can_place", (board, [[1]], row, col), True))
    invalid = [
        (-1, 0, [[1]]), (0, -1, [[1]]), (5, 0, [[1]]), (0, 5, [[1]]),
        (4, 4, [[1, 1]]), (4, 4, [[1], [1]]), (2, 2, [[1]]),
        (1, 1, [[1, 1]]), (3, 3, [[1], [1]]), (0, 0, [[1, 1, 1, 1, 1, 1]]),
    ]
    for index, (row, col, piece) in enumerate(invalid, 1):
        board = [[0] * 5 for _ in range(5)]
        if index == 7:
            board[2][2] = 1
        cases.append((f"can_place_invalid_{index:02d}", "can_place", (board, piece, row, col), False))

    # 놓기 10종은 결과 보드와 원본 불변성을 함께 검증한다.
    positions = [(0, 0), (0, 3), (1, 1), (1, 3), (2, 0), (2, 3), (3, 1), (3, 3), (4, 0), (4, 3)]
    for index, (row, col) in enumerate(positions, 1):
        board = [[0] * 5 for _ in range(5)]
        piece = [[1, 1]]
        expected = [line[:] for line in board]
        expected[row][col] = expected[row][col + 1] = 1
        cases.append((f"place_{index:02d}", "place", (board, piece, row, col), (expected, board)))

    # 0~3개 완성 줄을 섞어 보드 높이 복구, 줄 수, 비완성 행 보존을 확인한다.
    for index in range(15):
        height = 3 + index % 5
        width = 2 + index % 4
        full_count = index % 4
        full_positions = set(range(full_count))
        board = []
        for row in range(height):
            if row in full_positions:
                board.append([1] * width)
            else:
                partial = [int((row * 3 + col * 5 + index) % 4 == 0) for col in range(width)]
                if all(partial):
                    partial[0] = 0
                board.append(partial)
        kept = [line[:] for line in board if not all(line)]
        expected = [[0] * width for _ in range(full_count)] + kept
        cases.append((f"clear_lines_{index + 1:02d}", "clear_lines", board, (expected, full_count)))
    return cases


CASES = _build_cases()
assert len(CASES) == 100, f"benchmark must contain exactly 100 cases, got {len(CASES)}"


@pytest.mark.parametrize("case_id,kind,data,expected", CASES, ids=[case[0] for case in CASES])
def test_tetris_case(case_id, kind, data, expected):
    """각 독립 입력의 결과를 비교하고 원본 보드가 바뀌지 않는지 확인한다."""
    del case_id  # pytest ID에는 사용하고 본문에서는 사용하지 않는다.
    if kind == "rotate":
        assert tetris.rotate(data) == expected
    elif kind == "new_board":
        rows, cols = data
        board = tetris.new_board(rows, cols)
        assert len(board) == rows
        assert all(len(row) == cols for row in board)
        assert all(cell == 0 for row in board for cell in row)
    elif kind == "can_place":
        board, piece, row, col = data
        assert tetris.can_place(board, piece, row, col) is expected
    elif kind == "place":
        board, piece, row, col = data
        expected_board, original = expected
        assert tetris.place(board, piece, row, col) == expected_board
        assert board == original
    else:
        new_board, cleared = tetris.clear_lines(data)
        expected_board, expected_cleared = expected
        assert cleared == expected_cleared
        assert new_board == expected_board
        assert len(new_board) == len(data)
