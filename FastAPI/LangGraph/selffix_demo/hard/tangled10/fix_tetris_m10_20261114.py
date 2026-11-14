"""tetris_engine_mutations.py의 #10(hold) 두 번째 조각을 바꾼다 (2026-11-14).

이유: '        self.can_hold = True\\n        self.log' 가 정답 소스에 2번(__init__, record_clear) 있어
build 검증이 중단됐다. record_clear 쪽만 가리키도록 '.append'까지 넣는다.
source_patch가 이 폴더 파일에 적용되지 않아(원인 미확인) 정확한 문자열 치환으로 바꾼다. 원본은 .bak으로 남긴다.
"""
from pathlib import Path

PATH = Path(__file__).with_name("tetris_engine_mutations.py")
OLD = r'("        self.can_hold = True\n        self.log", "        self.can_hold = self.held is None\n        self.log")'
NEW = r'("        self.can_hold = True\n        self.log.append", "        self.can_hold = self.held is None\n        self.log.append")'

text = PATH.read_text(encoding="utf-8")
count = text.count(OLD)
if count != 1:
    raise SystemExit(f"바꿀 부분이 정확히 1번이 아님: {count}번 (아무것도 바꾸지 않음)")
PATH.with_suffix(".py.bak").write_text(text, encoding="utf-8")
PATH.write_text(text.replace(OLD, NEW), encoding="utf-8")
print("changed #10; backup:", PATH.with_suffix(".py.bak").name)
