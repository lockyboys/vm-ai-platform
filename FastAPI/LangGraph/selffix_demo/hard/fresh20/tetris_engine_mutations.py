"""테트리스 '새 얽힌 오류' 10개 (2026-11-14, LuckyBoys 요청: "새로 만들어야 되는거 아냐 벌써 해 봤잖아").

지난 시험(tangled10: 회전, 열 높이, piece_cells, 텍스트 왕복, 점수, 콤보, 레벨, 낙하, wall_kick, hold)과
겹치지 않는 함수·방식으로 새로 만들었다. 형식은 calc_engine_mutations.py와 같다.
"""

M = [
    (1, "번지는 오류", "full_rows·clear_lines", "full_rows가 블록이 하나라도 있는 행을 내고, clear_lines가 그 결과를 all()로 다시 걸러 맞춤",
     [("    return [y for y, row in enumerate(board) if all(row)]",
       "    return [y for y, row in enumerate(board) if any(row)]"),
      ("    kept = [row[:] for row in board if not all(row)]",
       "    full = {y for y in full_rows(board) if all(board[y])}\n"
       "    kept = [row[:] for y, row in enumerate(board) if y not in full]")]),
    (2, "번지는 오류(공유 참조)", "copy_board·place", "copy_board가 행을 복사하지 않고, place는 행을 한 번 더 복사해 덮음",
     [("    return [row[:] for row in board]", "    return list(board)"),
      ("    result = copy_board(board)\n    for r, c in piece_cells(piece):",
       "    result = [row[:] for row in copy_board(board)]\n    for r, c in piece_cells(piece):")]),
    (3, "짝 오류(방향)", "shift", "검사와 반환 모두 left - dx 로 바꿔 둘이 일관되게 반대 방향으로 움직임",
     [("    if can_place(board, piece, top, left + dx):\n        return left + dx",
       "    if can_place(board, piece, top, left - dx):\n        return left - dx")]),
    (4, "순서 오류", "bag_sequence", "조각 이름을 이름순이 아닌 사전 순서(I,O,T,...)로 섞어 같은 seed에서 순서가 달라짐",
     [("        bag = sorted(PIECES)", "        bag = list(PIECES)")]),
    (5, "짝 오류(방향)", "count_holes", "아래에서 위로 훑고 '블록 아래 빈칸' 대신 '블록 위 빈칸'을 셈",
     [("        for y in range(len(board)):\n            if board[y][x]:\n                seen_block = True",
       "        for y in reversed(range(len(board))):\n            if board[y][x]:\n                seen_block = True")]),
    (6, "경계값", "lines_to_next_level", "나머지를 total_lines-1로 구해 레벨 경계(0, 10, 20줄)에서 값이 틀림",
     [("    return LINES_PER_LEVEL - total_lines % LINES_PER_LEVEL",
       "    return LINES_PER_LEVEL - (total_lines - 1) % LINES_PER_LEVEL")]),
    (7, "상태 오류", "GameState.hold", "이전 보관 조각 대신 방금 넣은 조각을 돌려줌",
     [("        previous, self.held = self.held, current", "        self.held = current\n        previous = current")]),
    (8, "경계값", "is_game_over", "맨 위(0행)가 아니라 1행에 놓을 수 있는지로 판정",
     [("    return not can_place(board, piece, 0, left)", "    return not can_place(board, piece, 1, left)")]),
    (9, "범위 오류", "aggregate_height", "첫 열 높이를 빼고 합함",
     [("    return sum(column_heights(board))", "    return sum(column_heights(board)[1:])")]),
    (10, "상태 오류", "GameState.record_clear", "줄을 못 지웠을 때 콤보를 0으로 끊지 않고 1만 줄임",
     [("        else:\n            self.combo = 0", "        else:\n            self.combo = max(0, self.combo - 1)")]),
]
