"""스스로 고치는 리뷰 앱 시연용 테트리스 핵심 로직(화면 없음) (2026-11-10).

보드는 rows x cols 리스트(0=빈칸, 1=블록). 화면·입력 처리는 넣지 않아 테스트만으로 검증할 수 있다.
테스트: harness/tests/test_selffix_demo_tetris_20261110.py
공유 보드나 조각을 다른 실행 흐름이 변경할 수 있다면 호출자가 동기화해야 한다.
"""


def new_board(rows: int = 20, cols: int = 10) -> list[list[int]]:
    """빈 보드를 만든다."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    return [[0] * cols for _ in range(rows)]


def rotate(piece: list[list[int]]) -> list[list[int]]:
    """직사각형 조각을 시계 방향으로 90도 돌린다.

    빈 조각은 빈 리스트를 반환하고, 행 길이가 다르면 ValueError를 발생시킨다.
    """
    if not piece:
        return []
    width = len(piece[0])
    if any(len(row) != width for row in piece):
        raise ValueError("piece must be rectangular")
    return [list(row) for row in zip(*reversed(piece))]


def can_place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> bool:
    """채워진 조각 칸이 보드 안에 있고 기존 블록과 겹치지 않으면 True.

    불규칙한 보드는 각 행의 실제 길이를 기준으로 검사한다.
    """
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if not cell:
                continue
            y, x = top + r, left + c
            if y < 0 or y >= len(board) or x < 0 or x >= len(board[y]) or board[y][x]:
                return False
    return True


def place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> list[list[int]]:
    """조각을 놓은 새 보드를 돌려준다(원래 보드는 바꾸지 않는다).

    놓을 수 없으면 ValueError. 복사 중 입력의 동시 변경은 호출자가 방지해야 한다.
    """
    result = [row[:] for row in board]
    piece_snapshot = [row[:] for row in piece]
    if not can_place(result, piece_snapshot, top, left):
        raise ValueError("piece cannot be placed here")
    for r, row in enumerate(piece_snapshot):
        for c, cell in enumerate(row):
            if cell:
                result[top + r][left + c] = 1
    return result


def clear_lines(board: list[list[int]]) -> tuple[list[list[int]], int]:
    """가득 찬 줄을 지우고 위에 빈 줄을 채운 (새 보드, 지운 줄 수)를 돌려준다.

    빈 보드는 ([], 0)을 반환한다. 너비가 0이거나 행 길이가 다르면
    ValueError를 발생시킨다.
    """
    if not board:
        return [], 0
    cols = len(board[0])
    if cols == 0 or any(len(row) != cols for row in board):
        raise ValueError("board must be rectangular and have positive width")
    kept = [row[:] for row in board if not all(row)]
    cleared = len(board) - len(kept)
    return [[0] * cols for _ in range(cleared)] + kept, cleared