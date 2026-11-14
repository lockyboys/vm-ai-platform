"""비공개 키 구조 샘플 3건 출력 — 채점 키워드가 어떤 필드에 있는지 확인용."""
import base64, json, zlib
from pathlib import Path
pkg = json.loads(zlib.decompress(base64.b64decode("".join(Path("/data/vm_project/haness/apps/blind_review_judge_20261027/private_judge.b64").read_text().split()))))
pk = json.loads(pkg["private_key.json"])
items = list(pk.items())[:3]
for bid, info in items:
    print(json.dumps({bid: info}, ensure_ascii=False, indent=2))
    print("---")
# SCORING.md 도 출력
print("\n=== SCORING.md (앞 500자) ===")
print(pkg["SCORING.md"][:500])
