"""calc_engine_mutations.py의 #5(percent) 오류 정의를 바꾼다 (2026-11-14).

이유: 처음 설계(whole 절댓값)는 음수 whole 시험 식이 없어 드러나지 않았다(build 검증 실패).
바꾼 설계: percent가 100을 곱하지 않은 비율을 내고, percent_change가 그 percent에 100을 곱해 결과만 맞춘다.
source_patch가 이 파일에 적용되지 않아(원인 미확인) 정확한 문자열 치환으로 바꾼다. 원본은 .bak으로 남긴다.
"""
from pathlib import Path

PATH = Path(__file__).with_name("calc_engine_mutations.py")
OLD = ('    (5, "번지는 오류", "percent·percent_change", "percent가 whole의 절댓값으로 나누고, percent_change가 그 percent에 기대 결과만 맞춤",\n'
       '     [("    return part / whole * 100", "    return part / abs(whole) * 100"),\n'
       '      ("    return (new - old) / abs(old) * 100", "    return percent(new - old, old)")]),\n')
NEW = ('    (5, "번지는 오류", "percent·percent_change", "percent가 100을 곱하지 않은 비율을 내고, percent_change가 그 percent에 100을 곱해 결과만 맞춤",\n'
       '     [("    return part / whole * 100", "    return part / whole"),\n'
       '      ("    return (new - old) / abs(old) * 100", "    return percent(new - old, abs(old)) * 100")]),\n')

text = PATH.read_text(encoding="utf-8")
count = text.count(OLD)
if count != 1:
    raise SystemExit(f"바꿀 부분이 정확히 1번이 아님: {count}번 (아무것도 바꾸지 않음)")
PATH.with_suffix(".py.bak").write_text(text, encoding="utf-8")
PATH.write_text(text.replace(OLD, NEW), encoding="utf-8")
print("changed #5; backup:", PATH.with_suffix(".py.bak").name)
