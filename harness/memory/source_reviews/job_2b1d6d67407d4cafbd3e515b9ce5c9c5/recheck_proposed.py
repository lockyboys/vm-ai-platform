"""스스로 고치는 리뷰 앱 시연용 테트리스 핵심 로직(화면 없음) (2026-11-10).

보드는 rows x cols 리스트(0=빈칸, 1=블록). 화면·입력 처리는 넣지 않아 테스트만으로 검증할 수 있다.
시연용으로 넣었던 결함(rotate 회전 방향, clear_lines 높이 감소)은 수정되었다.
   테스트: harness/tests/test_selffix_demo_tetris_20261110.py
"""


def new_board(rows: int = 20, cols: int = 10) -> list[list[int]]:
    """빈 보드를 만든다."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    return [[0] * cols for _ in range(rows)]


def rotate(piece: list[list[int]]) -> list[list[int]]:
    """조각을 시계 방향으로 90도 돌린다."""
    # 수정 이유: 전치만 하면 대각선 반사가 된다. 행 순서를 뒤집은 뒤 전치해야 시계 방향 90도다.
    # 주의: 직사각형 조각을 전제한다(행 길이가 다르면 zip이 짧은 쪽에 맞춰 잘라낸다).
    return [list(row) for row in zip(*piece[::-1])]


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
    # 수정 이유: 지운 줄 수만큼 위에 빈 줄을 채워 보드 높이를 보존한다(높이가 줄면 can_place 경계가 틀어진다).
    # 주의: [[0] * cols] * cleared는 같은 행 객체를 공유하므로 컴프리헨션으로 행마다 새 리스트를 만든다.
    new_rows = [[0] * cols for _ in range(cleared)]
    return new_rows + kept, cleared