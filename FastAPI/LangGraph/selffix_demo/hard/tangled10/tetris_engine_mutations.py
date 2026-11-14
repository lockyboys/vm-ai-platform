"""테트리스 '얽힌 오류' 10개 (2026-11-14, LuckyBoys 요청: "복잡하게 얽히게 짜 오류를").

얽힘 설계 원칙은 calc_engine_mutations.py와 같다(짝 오류·번지는 오류·순서/상태 오류).
한쪽만 고치면 지금 통과하던 시험이 깨지므로, 관련된 곳을 함께 고쳐야 한다.
형식: (번호, 분야, 관련 함수, 설명, [(정답 코드, 결함 코드), ...]) — 조각은 순서대로 바꾼다.
"""

_CW = "    return [list(row) for row in zip(*piece[::-1])]"
_CCW = "    return [list(row) for row in zip(*piece)][::-1]"

M = [
    (1, "짝 오류(회전)", "rotate_cw·rotate_ccw", "시계·반시계 본문이 서로 바뀌어 180도 회전과 왕복 회전은 맞지만 각각은 반대",
     [(_CCW, "    @@CW_PLACEHOLDER@@"), (_CW, _CCW), ("    @@CW_PLACEHOLDER@@", _CW)]),
    (2, "번지는 오류", "column_heights·aggregate_height·max_height",
     "column_heights가 높이 대신 위에서 첫 블록까지 깊이(빈 열=행 수)를 내고, 쓰는 쪽 두 함수가 보정. bumpiness는 우연히 맞음",
     [("        height = 0", "        height = rows"),
      ("                height = rows - y", "                height = y"),
      ("    return sum(column_heights(board))", "    return len(board) * len(board[0]) - sum(column_heights(board))"),
      ("    return max(column_heights(board))", "    return len(board) - min(column_heights(board))")]),
    (3, "번지는 오류", "piece_cells·can_place·place·trim_piece", "piece_cells가 (열, 행)을 내고, 쓰는 세 함수가 모두 거꾸로 풀어 보정",
     [("    return [(r, c) for r, row in enumerate(piece)", "    return [(c, r) for r, row in enumerate(piece)"),
      ("    for r, c in piece_cells(piece):\n        y, x", "    for c, r in piece_cells(piece):\n        y, x"),
      ("    for r, c in piece_cells(piece):\n        result", "    for c, r in piece_cells(piece):\n        result"),
      ("    top = min(r for r, _ in cells)", "    top = min(r for _, r in cells)"),
      ("    bottom = max(r for r, _ in cells)", "    bottom = max(r for _, r in cells)"),
      ("    left = min(c for _, c in cells)", "    left = min(c for c, _ in cells)"),
      ("    right = max(c for _, c in cells)", "    right = max(c for c, _ in cells)")]),
    (4, "짝 오류(왕복)", "board_to_text·text_to_board", "아래 행부터 쓰고 거꾸로 읽어 왕복은 맞지만 각각은 위아래가 뒤집힘",
     [('"".join("#" if cell else "." for cell in row) for row in board)',
       '"".join("#" if cell else "." for cell in row) for row in board[::-1])'),
      ("    return board\n\n\n# ---------------------------------------------------------------- 조각",
       "    return board[::-1]\n\n\n# ---------------------------------------------------------------- 조각")]),
    (5, "짝 오류(점수)", "score_for_lines·GameState.record_clear", "점수식이 level+1 대신 level을 곱하고, record_clear가 level+1을 넘겨 게임 점수만 맞춤",
     [("    return LINE_SCORES[cleared] * (level + 1)", "    return LINE_SCORES[cleared] * level"),
      ("        gained = score_for_lines(cleared, level)", "        gained = score_for_lines(cleared, level + 1)")]),
    (6, "짝 오류(콤보)", "combo_bonus·GameState.record_clear", "보너스가 combo-1 기준으로 바뀌고, record_clear가 combo를 그대로 넘겨 게임 안에서만 맞춤",
     [("    if combo <= 0:\n        return 0\n    return 50 * combo * (level + 1)",
       "    if combo <= 1:\n        return 0\n    return 50 * (combo - 1) * (level + 1)"),
      ("combo_bonus(self.combo - 1, level)", "combo_bonus(self.combo, level)")]),
    (7, "번지는 오류", "level_for_lines·GameState.level", "level_for_lines가 한 줄 일찍 레벨을 올리고, GameState.level이 lines-1로 보정",
     [("    return total_lines // LINES_PER_LEVEL", "    return (total_lines + 1) // LINES_PER_LEVEL"),
      ("        return self.start_level + level_for_lines(self.lines)",
       "        return self.start_level + (level_for_lines(self.lines - 1) if self.lines else 0)")]),
    (8, "짝 오류(낙하)", "drop_row·hard_drop", "drop_row가 한 칸 더 내려간 행을 내고, hard_drop이 1을 빼 보정",
     [("    return top\n\n\ndef hard_drop", "    return top + 1\n\n\ndef hard_drop"),
      ("    landing = drop_row(board, piece, left, top)", "    landing = drop_row(board, piece, left, top) - 1")]),
    (9, "짝 오류(좌표)", "wall_kick", "기본 시도표를 (열, 행)으로 적고 반복문도 (dx, dy)로 풀어 기본값은 맞지만, 직접 넘긴 offsets는 축이 바뀜",
     [("offsets=((0, 0), (0, -1), (0, 1), (-1, 0))", "offsets=((0, 0), (-1, 0), (1, 0), (0, -1))"),
      ("    for dy, dx in offsets:", "    for dx, dy in offsets:")]),
    (10, "상태 짝 오류", "GameState.hold·record_clear", "hold의 차단 조건을 '보관 조각이 있을 때만'으로 바꾸고, 놓은 뒤 보관 가능 여부를 보관 조각 유무로 정함",
     [("        if not self.can_hold:", "        if self.held is not None and not self.can_hold:"),
      ("        self.can_hold = True\n        self.log.append", "        self.can_hold = self.held is None\n        self.log.append")]),
]
