"""Gemini blind review 진행 상황 확인. job별 결과 디렉터리와 기존 공용 디렉터리 양쪽을 센다."""
import json
from pathlib import Path

ROOT = Path("/data/vm_project/haness/apps/blind_review_20261027")
# 신규: job 별 디렉터리 (job_output_dir 반영 후)
job_dir = ROOT / "results" / "gemini" / "jobs"
# 구형: 공용 디렉터리
flat_dir = ROOT / "results" / "gemini"

for label, d in [("job dirs", job_dir), ("flat dir", flat_dir)]:
    if not d.exists():
        print(f"{label}: 없음")
        continue
    jsons = sorted(d.glob("*.json"))
    # summary.json 은 카운트에서 제외
    result_files = [f for f in jsons if f.name != "summary.json"]
    success = sum(1 for f in result_files if json.loads(f.read_text()).get("success") is True)
    print(f"{label}: {len(result_files)} files, {success} success  ({d})")
    # job 하위 디렉터리도 확인
    for sub in sorted(d.iterdir()):
        if sub.is_dir():
            sub_jsons = [f for f in sub.glob("*.json") if f.name != "summary.json"]
            sub_ok = sum(1 for f in sub_jsons if json.loads(f.read_text()).get("success") is True)
            print(f"  └─ {sub.name}: {len(sub_jsons)} files, {sub_ok} success")
    # summary 내용도 출력
    s = d / "summary.json"
    if s.exists():
        sm = json.loads(s.read_text())
        print(f"  summary: status={sm.get('status')} completed={sm.get('completed')} total={sm.get('total')}")
