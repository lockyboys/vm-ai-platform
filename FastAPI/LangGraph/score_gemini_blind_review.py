"""블라인드 리뷰 Gemini 채점 스크립트 (2026-10-30).

목적: private_judge.b64 에 담긴 비공개 결함 카탈로그와 Gemini 82건 응답 원문을 매핑하고,
      주입 결함을 구체적으로 식별했는지 판정해 80점 만점 점수를 산출한다.
      정상 대조 2건에 대한 오진(false positive)은 별도 집계한다.
이유: 보고서 6장 품질 점수 산출 조건을 충족하기 위해.
주의: 비공개 패키지 구조에 따라 키 이름이 다를 수 있어 먼저 구조를 출력한다.
"""
import base64, json, zlib
from pathlib import Path

# 비공개 채점 기준 로드
JUDGE_PATH = Path("/data/vm_project/haness/apps/blind_review_judge_20261027/private_judge.b64")
raw = "".join(JUDGE_PATH.read_text().split())
judge = json.loads(zlib.decompress(base64.b64decode(raw)))

# Gemini 결과 디렉터리 (신규 job별 격리 경로)
RESULT_DIR = Path("/data/vm_project/haness/apps/blind_review_20261027/results/gemini/jobs/cc319de2752c4649a13e1834a2c0c864")

# 1단계: 비공개 패키지 구조 출력 (키·샘플)
print("=== judge 패키지 구조 ===")
print(f"최상위 키: {list(judge.keys())}")
for k, v in judge.items():
    if isinstance(v, list):
        print(f"  {k}: list[{len(v)}], 첫 항목 키={list(v[0].keys()) if v and isinstance(v[0], dict) else 'N/A'}")
    elif isinstance(v, dict):
        print(f"  {k}: dict 키={list(v.keys())[:5]}...")
    else:
        print(f"  {k}: {type(v).__name__} = {str(v)[:100]}")

# 2단계: 결과 파일 로드
results = {}
for f in sorted(RESULT_DIR.glob("*.json")):
    if f.name == "summary.json":
        continue
    r = json.loads(f.read_text())
    results[r["id"]] = r

print(f"\n=== 결과 파일 ===")
print(f"로드된 결과: {len(results)}건")
print(f"성공 결과: {sum(1 for r in results.values() if r.get('success'))}건")

# 3단계: 채점 (비공개 카탈로그 구조에 맞춰 동적으로 처리)
# 결함 케이스 = id가 정상 대조 id가 아닌 것
# 정상 대조 = judge 에 normal/clean/correct 등으로 표기된 것
catalog = judge.get("catalog") or judge.get("cases") or judge.get("defects") or judge.get("items") or []
if not catalog:
    # 키를 못 찾았으면 전체 구조를 덤프
    print("\n⚠️ 카탈로그 키를 찾지 못했습니다. 전체 구조:")
    print(json.dumps({k: type(v).__name__ for k, v in judge.items()}, ensure_ascii=False))
else:
    detected = 0
    false_positives = 0
    missed = []
    for case in catalog:
        case_id = case.get("id") or case.get("case_id") or case.get("file_id")
        is_normal = case.get("type") in ("normal", "clean", "correct") or case.get("defect_count", 1) == 0
        response_text = results.get(case_id, {}).get("response", "")
        # 결함 키워드가 응답에 있는지 확인
        keywords = case.get("keywords") or case.get("defect_keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        found = any(kw.lower() in response_text.lower() for kw in keywords) if keywords else bool(response_text)

        if is_normal:
            if found and keywords:
                false_positives += 1
        else:
            if found:
                detected += 1
            else:
                missed.append(case_id)

    total_defects = sum(1 for c in catalog if c.get("type") not in ("normal", "clean", "correct") and c.get("defect_count", 1) != 0)
    print(f"\n=== Gemini 채점 결과 ===")
    print(f"총 결함 케이스: {total_defects}")
    print(f"검출 성공: {detected}/{total_defects} ({detected}점)")
    print(f"오진 (정상→결함): {false_positives}")
    print(f"미검출: {len(missed)}건")
    if missed:
        print(f"미검출 ID(최대 10개): {missed[:10]}")

print("\n완료")
