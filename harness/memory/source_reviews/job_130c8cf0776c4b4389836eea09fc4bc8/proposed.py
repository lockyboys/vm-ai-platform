"""스스로 고치는 리뷰 앱 시연용 테트리스 핵심 로직(화면 없음) (2026-11-10).

보드는 rows x cols 리스트(0=빈칸, 1=블록). 화면·입력 처리는 넣지 않아 테스트만으로 검증할 수 있다.
⚠ 시연을 위해 일부러 넣은 결함이 수정되었습니다.
   테스트: harness/tests/test_selffix_demo_tetris_20261110.py
"""


def new_board(rows: int = 20, cols: int = 10) -> list[list[int]]:
    """빈 보드를 만든다."""
    if rows < 1 or cols < 1:
        raise ValueError("rows and cols must be positive")
    return [[0] * cols for _ in range(rows)]


def rotate(piece: list[list[int]]) -> list[list[int]]:
    """조각을 시계 방향으로 90도 돌린다. (수정됨)"""
    # [수정 근거] 기존 코드는 단순 전치(Transpose)만 수행하여 시계 방향 회전이 아니었다.
    # 시계 방향 90도 회전을 위해서는 전치(zip(*piece)) 후, 각 행을 역순으로 뒤집어야 한다.
    return [list(reversed(row)) for row in zip(*piece)]


def can_place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> bool:
    """조각이 보드 안에 있고 기존 블록과 겹치지 않으면 True."""
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if not cell:
                continue
            y, x = top + r, left + c
            # 경계 조건 검사: y 또는 x가 보드 범위를 벗어나는지 확인
            if y < 0 or y >= len(board) or x < 0 or x >= len(board[0]):
                return False
            # 충돌 검사: 해당 위치에 이미 블록이 있는지 확인
            if board[y][x]:
                return False
    return True


def place(board: list[list[int]], piece: list[list[int]], top: int, left: int) -> list[list[int]]:
    """조각을 놓은 새 보드를 돌려준다(원래 보드는 바꾸지 않는다). 놓을 수 없으면 ValueError."""
    if not can_place(board, piece, top, left):
        raise ValueError("piece cannot be placed here")
    # 원본 보드를 변경하지 않기 위해 깊은 복사(Deep Copy)를 수행한다.
    result = [row[:] for row in board]
    for r, row in enumerate(piece):
        for c, cell in enumerate(row):
            if cell:
                result[top + r][left + c] = 1
    return result


def clear_lines(board: list[list[int]]) -> tuple[list[list[int]], int]:
    """가득 찬 줄을 지우고 위에 빈 줄을 채운 (새 보드, 지운 줄 수)를 돌려준다. (수정됨)"""
    cols = len(board[0])
    
    # 가득 찬 줄을 제외한 나머지 줄들만 'kept' 리스트에 복사한다.
    kept = [row[:] for row in board if not all(row)]
    cleared = len(board) - len(kept)
    
    # [수정 근거] 지운 줄 수(cleared)만큼 빈 행을 생성하고, 이를 'kept' 리스트 앞에 추가하여 보드 높이를 복원한다.
    padding = [[0] * cols for _ in range(cleared)]
    new_board = padding + kept
    
    return new_board, cleared