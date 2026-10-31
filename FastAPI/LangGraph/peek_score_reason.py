"""채점 결과 첫 2건의 reason만 출력."""
import json
from pathlib import Path
SCORE_DIR = Path("/data/vm_project/haness/apps/blind_review_20261027/results/gemini/jobs/cc319de2752c4649a13e1834a2c0c864/scoring_packages/scores")
for f in sorted(SCORE_DIR.glob("*_scores.json"))[:1]:
    data = json.loads(f.read_text())
    for item in data[:2]:
        print(f"{item['case_id']}: score={item['score']}, reason={item['reason'][:200]}")
