"""스스로 고치는 리뷰 앱 시연용 테트리스 핵심 로직(화면 없음) (2026-11-10).

보드는 rows x cols 리스트(0=빈칸, 1=블록). 화면·입력 처리는 넣지 않아 테스트만으로 검증할 수 있다.
⚠ 시연을 위해 일부러 넣은 결함이 있다(review_python_source가 찾아 고치는지 확인용).
   테스트: harness/tests/test_selffix_demo_tetris_20261110.py
"""


def new_board(rows: int = 20, cols: int = 10) -> list[list[int]]:
    """빈 보드를 만든다."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    return [[0] * cols for _ in range(rows)]


def rotate(piece: list[list[int]]) -> list[list[int]]:
    """조각을 시계 방향으로 90도 돌린다."""
    return [list(row) for row in zip(*piece)]  # 결함: 전치만 하고 좌우 뒤집기를 안 해 시계 방향이 아니다


def can_place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> bool:
    """조각이 보드 안에 있고 기존 블록과 겹치지 않으면 True."""
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if not cell:
                continue
            y, x = top + r, left + c
            if y < 0 or y >= len(board) or x < 0 or x >= len(board[0]) or board[y][x]:
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
    cols = len(board[0])
    kept = [row[:] for row in board if not all(row)]
    cleared = len(board) - len(kept)
    return kept, cleared  # 결함: 지운 만큼 위에 빈 줄을 채우지 않아 보드 높이가 줄어든다
