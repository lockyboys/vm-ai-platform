"""블라인드 리뷰 LLM 판독 채점 (2026-10-30).

SCORING.md 기준: 주입 결함의 '실제 변경 위치/연산과 그 문제를 구체적으로 지적'하면 1점.
이 스크립트는 scoring_packages/<category>.json 의 각 건에 대해
Gemini로 판독 질의를 보내고 {score:0|1, reason:""} 을 받아 집계한다.

범주별로 순차 실행하며, 이미 채점된 건은 건너뛴다.
"""
import json, os, time
import re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv("/data/vm_project/.env", override=False)
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
if not key:
    raise ValueError("Gemini credential absent")

# 채점 전용 모델 (temperature 0, 짧은 출력)
llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash", api_key=SecretStr(key),
    temperature=0, max_output_tokens=256, thinking_budget=0, max_retries=2, timeout=120
)

PACKAGES_DIR = Path("/data/vm_project/haness/apps/blind_review_20261027/results/gemini/jobs/cc319de2752c4649a13e1834a2c0c864/scoring_packages")
SCORE_DIR = PACKAGES_DIR / "scores"
SCORE_DIR.mkdir(exist_ok=True)

JUDGE_PROMPT = """당신은 코드 리뷰 채점관입니다.

아래에 주입된 결함 설명과 모델의 리뷰 응답이 있습니다.
결함 설명: {description}
앱: {app}, 케이스: {case_id}
검증 정보: {verification}

=== 모델 응답 (앞 2500자) ===
{response}
===

판정 기준: 모델이 이 주입 결함의 실제 변경 위치나 연산과 그 문제를 구체적으로 지적했으면 1점, 아니면 0점.
일반적인 개선 제안, 무관한 결함, 단순 소스 인용은 0점.

반드시 아래 JSON 형식만 출력하세요 (다른 텍스트 없이):
{{"score": 0 또는 1, "reason": "판정 근거 한 줄"}}"""

total_score = 0
total_cases = 0
category_scores = {}

for cat_file in sorted(PACKAGES_DIR.glob("*.json")):
    cat = cat_file.stem
    entries = json.loads(cat_file.read_text())
    score_file = SCORE_DIR / f"{cat}_scores.json"

    # 이미 채점 완료된 건 로드
    existing = {}
    if score_file.exists():
        for s in json.loads(score_file.read_text()):
            existing[s["blind_id"]] = s

    scored = list(existing.values())
    for entry in entries:
        bid = entry["blind_id"]
        if bid in existing:
            continue  # 이미 채점됨

        prompt = JUDGE_PROMPT.format(
            description=entry.get("description", ""),
            app=entry.get("app", ""),
            case_id=entry.get("case_id", ""),
            verification=json.dumps(entry.get("verification", {}), ensure_ascii=False)[:500],
            response=entry.get("response", "")[:2500]
        )

        try:
            raw = llm.invoke(prompt)
            text = raw.content if isinstance(raw.content, str) else str(raw.content)
            # JSON 추출
            text = text.strip()
            if text.startswith("```"): text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            # 1차: 엄격 JSON
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # 2차: 작은따옴표→큰따옴표
                try:
                    result = json.loads(text.replace("'", '"'))
                except json.JSONDecodeError:
                    m = re.search(r'"?score"?\s*:\s*(\d)', text)
                    result = {"score": int(m.group(1)), "reason": text[:100]} if m else {"score": 0, "reason": f"파싱불가: {text[:100]}"}
            sc = 1 if result.get("score") in (1, "1") else 0
            reason = str(result.get("reason", ""))
        except Exception as e:
            sc = 0; reason = f"판독 실패: {e}"

        scored.append({"blind_id": bid, "case_id": entry["case_id"], "app": entry["app"],
                        "score": sc, "reason": reason})
        # 건별 저장 (중단 시 재개 가능)
        score_file.write_text(json.dumps(scored, ensure_ascii=False, indent=2))
        time.sleep(0.5)  # rate limit 방지

    cat_detected = sum(1 for s in scored if s["score"] == 1)
    cat_total = len(scored)
    category_scores[cat] = {"detected": cat_detected, "total": cat_total}
    total_score += cat_detected
    total_cases += cat_total
    print(f"{cat}: {cat_detected}/{cat_total}")

print(f"\n=== 최종 Gemini 채점 ===")
print(f"총점: {total_score}/{total_cases}")
print(f"검출율: {total_score/total_cases*100:.1f}%" if total_cases else "N/A")

# 최종 결과 저장
final = {"provider": "gemini", "model": "gemini-3.8-flash", "scorer": "gemini-2.5-flash",
         "total_score": total_score, "max_score": total_cases,
         "detection_rate": round(total_score/total_cases*100, 1) if total_cases else 0,
         "by_category": category_scores}
(SCORE_DIR / "final_score.json").write_text(json.dumps(final, ensure_ascii=False, indent=2))
print(f"\n저장: {SCORE_DIR / 'final_score.json'}")
