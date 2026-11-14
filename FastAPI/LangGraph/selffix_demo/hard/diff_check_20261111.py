"""자가 수정 결과 '찜찜한 점' 점검: 채점 식에 없는 무작위 입력으로 정답 구현과 비교 (2026-11-11, LuckyBoys 요청).

왜 필요한가
- 자동 적용 판정에 쓴 채점 식(계산기 274, 테트리스 188)을 AI가 피드백으로 봤다.
  그래서 "채점 식만 통과하도록 맞춘 것(과적합)"인지, 진짜로 명세대로 고쳐졌는지 따로 확인해야 한다.
- 방법(차분 시험): 정답 구현(_build/<program>_ref.py)과 고쳐진 파일에 같은 무작위 입력을 넣고
  결과(값 또는 예외 종류)가 같은지 본다. 채점 식과 다른 새 입력이라 외워서는 통과할 수 없다.

안전: LLM 호출 없음. 파일은 읽기만 한다(새 모듈로 exec). 입력 하나당 1초 제한(무한 반복 대비).
실행: python FastAPI/LangGraph/selffix_demo/hard/diff_check_20261111.py
"""
import json
import random
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
sys.path.insert(0, str(ROOT))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402

HARD = ROOT / "FastAPI/LangGraph/selffix_demo/hard"
SAMPLES_PER_FUNCTION = 300  # 함수마다 무작위 입력 수
SEED = 20261111             # 같은 결과를 다시 재현할 수 있게 고정
# 점검 대상: 채점 식을 모두 통과해 '다 고쳤다'고 판정된 파일 + 비교용(남은 오류 1건) 파일
TARGETS = ["calc_engine_openai", "calc_engine_claude", "calc_engine_gemini",
           "tetris_engine_openai", "tetris_engine_claude"]


def _load(path: Path):
    module = types.ModuleType(path.stem)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)  # noqa: S102
    return module


# ------------------------------------------------------------ 무작위 입력 생성(인자 튜플 목록)
def _num(rng):
    return rng.choice([rng.randint(-50, 50), round(rng.uniform(-50, 50), rng.randint(0, 3)), 0, 0.0, 1, -1])


def calc_inputs(rng):
    """계산기 함수별 무작위 호출 식 목록(문자열, m = 대상 모듈)."""
    lists = lambda: [_num(rng) for _ in range(rng.randint(0, 6))]  # noqa: E731
    exprs = []
    for _ in range(SAMPLES_PER_FUNCTION):
        a, b, c = _num(rng), _num(rng), _num(rng)
        n = rng.randint(-5, 30)
        exprs += [f"m.add({a!r}, {b!r})", f"m.subtract({a!r}, {b!r})", f"m.multiply({a!r}, {b!r})",
                  f"m.divide({a!r}, {b!r})", f"m.floor_divide({a!r}, {b!r})", f"m.modulo({a!r}, {b!r})",
                  f"m.power({a!r}, {rng.choice([n, 0.5, -2, 3])!r})", f"m.reciprocal({a!r})",
                  f"m.absolute({a!r})", f"m.average_of_two({a!r}, {b!r})",
                  f"m.round_half_up({a!r}, {rng.choice([0, 1, 2, 3, -1])!r})", f"m.truncate({a!r})",
                  f"m.ceil_divide({int(a)!r}, {int(b)!r})", f"m.clamp({a!r}, {min(b, c)!r}, {max(b, c)!r})",
                  f"m.clamp({a!r}, {b!r}, {c!r})", f"m.percent({a!r}, {b!r})", f"m.percent_change({a!r}, {b!r})",
                  f"m.mean({lists()!r})", f"m.median({lists()!r})", f"m.mode({[rng.randint(-3, 3) for _ in range(rng.randint(0, 7))]!r})",
                  f"m.variance({lists()!r})", f"m.value_range({lists()!r})", f"m.cumulative_sum({lists()!r})",
                  f"m.weighted_mean({lists()!r}, {[abs(x) for x in lists()]!r})",
                  f"m.moving_average({lists()!r}, {rng.randint(-1, 5)})",
                  f"m.factorial({rng.randint(-3, 15)})", f"m.gcd({rng.randint(-60, 60)}, {rng.randint(-60, 60)})",
                  f"m.lcm({rng.randint(-30, 30)}, {rng.randint(-30, 30)})", f"m.is_prime({rng.randint(-5, 400)})",
                  f"m.primes_up_to({rng.randint(-3, 120)})", f"m.fibonacci({rng.randint(-2, 40)})",
                  f"m.digit_sum({rng.randint(-99999, 99999)})", f"m.is_palindrome_number({rng.randint(-2000, 20000)})",
                  f"m.parse_number({rng.choice(['12', ' -7 ', '+3', '4.25', '1e2', 'abc', '', 'inf', 'nan', '1 2', '0', '-0.5', '.5', str(n)])!r})",
                  f"m.format_thousands({rng.randint(-10**9, 10**9)})", f"m.to_binary({rng.randint(-300, 300)})",
                  f"m.from_binary({rng.choice(['0', '1', '101', '-110', '', '-', '12', '1111', format(rng.randint(0, 999), 'b')])!r})",
                  f"m.celsius_to_fahrenheit({a!r})", f"m.fahrenheit_to_celsius({a!r})", f"m.km_to_miles({a!r})"]
        ops = "+-*/"
        expr = f"{rng.randint(0, 9)}"
        for _ in range(rng.randint(0, 4)):
            expr += f" {rng.choice(ops)} {rng.choice([str(rng.randint(0, 9)), '(' + str(rng.randint(1, 9)) + ' - ' + str(rng.randint(0, 9)) + ')', '-' + str(rng.randint(1, 9))])}"
        exprs += [f"m.evaluate({expr!r})", f"m.tokenize({expr!r})"]
        seq = [(rng.choice("+-*/%"), rng.choice([0, 1, 2, -3, 2.5])) for _ in range(rng.randint(1, 5))]
        steps = ", ".join(f"attempt(lambda: c.apply({op!r}, {v!r}))" for op, v in seq)
        exprs.append(f"(lambda c: ({steps}, attempt(c.undo), c.memory_add(), c.memory_recall(), c.value, c.history))(m.Calculator({_num(rng)!r}))")
    return exprs


def _board(rng, rows, cols, p):
    return "|".join("".join("x" if rng.random() < p else "." for _ in range(cols)) for _ in range(rows))


def tetris_inputs(rng):
    """테트리스 함수별 무작위 호출 식 목록."""
    pieces = ["m.PIECES['I']", "m.PIECES['O']", "m.PIECES['T']", "m.PIECES['S']", "m.PIECES['Z']",
              "m.PIECES['J']", "m.PIECES['L']", "[[1]]", "[[1], [1]]", "[[0, 1], [1, 1]]"]
    exprs = []
    for _ in range(SAMPLES_PER_FUNCTION):
        rows, cols = rng.randint(1, 6), rng.randint(1, 6)
        b = f"B({_board(rng, rows, cols, rng.choice([0, 0.2, 0.5, 0.9]))!r})"
        p = rng.choice(pieces)
        t, left = rng.randint(-1, rows), rng.randint(-1, cols)
        grid = [[rng.randint(0, 9) for _ in range(rng.randint(1, 4))]] * 1
        width = rng.randint(1, 4)
        grid = [[rng.randint(0, 9) for _ in range(width)] for _ in range(rng.randint(1, 4))]
        exprs += [f"m.new_board({rng.randint(-1, 6)}, {rng.randint(-1, 6)})", f"m.copy_board({b})",
                  f"m.board_to_text({b})", f"m.text_to_board(m.board_to_text({b}))",
                  f"m.rotate_cw({grid!r})", f"m.rotate_ccw({grid!r})", f"m.rotate_180({grid!r})",
                  f"m.piece_cells({grid!r})", f"m.trim_piece({[[rng.randint(0, 1) for _ in range(width)] for _ in range(3)]!r})",
                  f"m.piece_size({grid!r})", f"m.can_place({b}, {p}, {t}, {left})",
                  f"attempt(lambda: m.place({b}, {p}, {t}, {left}))", f"m.full_rows({b})", f"m.clear_lines({b})",
                  f"attempt(lambda: m.drop_row({b}, {p}, {left}))", f"attempt(lambda: m.hard_drop({b}, {p}, {left}))",
                  f"m.shift({b}, {p}, {t}, {left}, {rng.randint(-2, 2)})", f"m.wall_kick({b}, {p}, {t}, {left})",
                  f"m.is_game_over({b}, {p}, {left})", f"m.column_heights({b})", f"m.aggregate_height({b})",
                  f"m.max_height({b})", f"m.count_holes({b})", f"m.bumpiness({b})",
                  f"m.score_for_lines({rng.randint(-1, 5)}, {rng.randint(-1, 12)})",
                  f"m.level_for_lines({rng.randint(-3, 99)})", f"m.lines_to_next_level({rng.randint(0, 99)})",
                  f"m.gravity_frames({rng.randint(0, 15)})", f"m.combo_bonus({rng.randint(-2, 6)}, {rng.randint(0, 5)})",
                  f"m.bag_sequence({rng.randint(-1, 30)}, {rng.randint(0, 50)})"]
        clears = [rng.randint(0, 4) for _ in range(rng.randint(1, 15))]
        holds = rng.choice(["", "g.hold('T'), ", "g.hold('T'), attempt(lambda: g.hold('S')), "])
        exprs.append(f"(lambda g: ({holds}[g.record_clear(n) for n in {clears!r}], g.score, g.lines, g.level, g.combo, g.held, g.can_hold, g.log))(m.GameState({rng.randint(0, 3)}))")
    return exprs


def check(program, target, ref, exprs):
    """같은 식을 정답·대상에 넣고 다른 결과를 함수 이름별로 모은다."""
    module = _load(HARD / f"{target}.py")
    diffs = {}
    for expr in exprs:
        want, got = bs.run_case(ref, expr), bs.run_case(module, expr)
        if not bs.matches(got, want):
            name = expr.split("(", 1)[0].replace("m.", "") if expr.startswith("m.") else "stateful/attempt"
            bucket = diffs.setdefault(name, {"count": 0, "example": None})
            bucket["count"] += 1
            bucket["example"] = bucket["example"] or {"expr": expr[:200], "want": repr(want)[:150], "got": repr(got)[:150]}
    return {"target": target, "inputs": len(exprs), "mismatches": sum(d["count"] for d in diffs.values()),
            "by_function": diffs}


def main():
    rng = random.Random(SEED)
    inputs = {"calc_engine": calc_inputs(rng), "tetris_engine": tetris_inputs(rng)}
    refs = {p: _load(HARD / "_build" / f"{p}_ref.py") for p in inputs}
    results = []
    for target in TARGETS:
        program = "calc_engine" if target.startswith("calc") else "tetris_engine"
        results.append(check(program, target, refs[program], inputs[program]))
    # 자기 점검: 정답끼리는 차이가 0이어야 하고, 결함 원본은 차이가 나야 이 시험이 의미가 있다.
    sanity = {p: {"ref_vs_ref": check(p, f"_build/{p}_ref", refs[p], inputs[p])["mismatches"],
                  "ref_vs_original": check(p, f"{p}_original", refs[p], inputs[p])["mismatches"]} for p in inputs}
    print(json.dumps({"sanity": sanity, "results": results}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
