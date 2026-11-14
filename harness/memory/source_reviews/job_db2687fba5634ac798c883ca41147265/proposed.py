"""스스로 고치는 리뷰 앱 시연용 테트리스 핵심 로직(화면 없음) (2026-11-10).

보드는 rows x cols 리스트(0=빈칸, 1=블록). 화면·입력 처리는 넣지 않아 테스트만으로 검증할 수 있다.
테스트: harness/tests/test_selffix_demo_tetris_20261110.py
"""


def new_board(rows: int = 20, cols: int = 10) -> list[list[int]]:
    """빈 보드를 만든다."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    return [[0] * cols for _ in range(rows)]


def rotate(piece: list[list[int]]) -> list[list[int]]:
    """조각을 시계 방향으로 90도 돌린다."""
    if not piece or not piece[0]:
        return []
    # 단순 전치(zip(*piece)) 대신 상하를 뒤집은 뒤 전치하여 90도 시계 방향 회전을 완성한다.
    return [list(row) for row in zip(*piece[::-1])]


def can_place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> bool:
    """조각이 보드 안에 있고 기존 블록과 겹치지 않으면 True."""
    if not board or not board[0]:
        return False
    board_rows = len(board)
    board_cols = len(board[0])
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if not cell:
                continue
            y, x = top + r, left + c
            if y < 0 or y >= board_rows or x < 0 or x >= board_cols or board[y][x]:
                return False
    return True


def place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> list[list[int]]:
    """조각을 놓은 새 보드를 돌려준다(원래 보드는 바꾸지 않는다). 놓을 수 없으면 ValueError."""
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed here")
    result = [row[:] for row in board]
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if cell:
                result[top + r][left + c] = 1
    return result


def clear_lines(board: list[list[int]]) -> tuple[list[list[int]], int]:
    """가득 찬 줄을 지우고 위에 빈 줄을 채운 (새 보드, 지운 줄 수)를 돌려준다."""
    if not board or not board[0]:
        return [], 0
    cols = len(board[0])
    kept = [row[:] for row in board if not all(row)]
    cleared = len(board) - len(kept)
    # 지운 줄(cleared)만큼 상단에 0으로 채워진 빈 줄을 추가해 원래 보드 행 높이를 유지한다.
    empty_lines = [[0] * cols for _ in range(cleared)]
    return empty_lines + kept, cleared