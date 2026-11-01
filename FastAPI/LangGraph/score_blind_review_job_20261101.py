"""블라인드 리뷰 job 채점 — 결과 폴더를 입력으로 받는 일반화 버전 (2026-11-01, LuckyBoys: Ollama 점수·Gemini 비교).

기존 prepare_scoring_packages.py + llm_judge_gemini_scoring.py 는 Gemini job(cc319de2…) 경로가 고정돼 있어
Ollama job에 쓸 수 없다. 원본은 그대로 두고, 같은 채점 조건을 이 파일 하나에 옮겼다:
  - 정답 키: haness/apps/blind_review_judge_20261027/private_judge.b64 (private_key.json + verification.json)
  - 판독 프롬프트(JUDGE_PROMPT) 문구: llm_judge_gemini_scoring.py 와 글자 단위로 동일
  - 채점 모델: gemini-3.8-flash, temperature 0, max_output_tokens 256, thinking_budget 0, max_retries 2, timeout 120
  - 응답 길이: 패키지에 앞 3000자 저장 → 판독 시 앞 2500자 사용 (기존과 동일)
차이(버그 방지):
  - 결과 폴더의 *.attemptN.json(실패 보존본)과 summary.json 은 읽지 않는다 → 최종 결과 파일만 채점
  - 결과 파일이 없거나 success=false 인 건은 판독하지 않고 0점 + reason 기록(없는 응답을 채점관이 추측하지 않게)
입력(stdin JSON): {"provider": "ollama"|"gemini", "job_id": "<32 hex>", "dry_run": true|false}
  dry_run=true : 패키지만 만들고 건수·누락만 보고(Gemini 호출 없음)
출력: <결과폴더>/scoring_packages/<category>.json, scores/<category>_scores.json, scores/final_score.json
      이미 채점된 건은 건너뛴다(중단 후 재실행 가능).
"""
import base64
import json
import os
import re
import sys
import time
import zlib
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4) — PROJECT_ROOT

ROOT = Path(config.PROJECT_ROOT)
JUDGE_PACKAGE = ROOT / "haness/apps/blind_review_judge_20261027/private_judge.b64"
SCORER_MODEL = "gemini-3.8-flash"  # Gemini 80/82 채점 때와 같은 모델

# llm_judge_gemini_scoring.py 의 프롬프트를 그대로 복사(비교 조건 동일 유지 — 문구 수정 금지)
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


def parse_request() -> tuple[str, str, bool]:
    """입력 검증: provider 두 종류, job_id 32자리 소문자 hex(경로 이탈 차단), dry_run bool."""
    req = json.loads(sys.stdin.read() or "{}")
    provider, job_id, dry_run = req.get("provider"), req.get("job_id"), req.get("dry_run", True)
    if provider not in ("ollama", "gemini"):
        raise ValueError("provider must be ollama or gemini")
    if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError("job_id must be 32 lowercase hex characters")
    if not isinstance(dry_run, bool):
        raise ValueError("dry_run must be true or false")
    return provider, job_id, dry_run


def load_results(result_dir: Path) -> dict:
    """최종 결과 파일만 읽는다. attempt 보존본·summary·score 파일은 제외."""
    results = {}
    for f in sorted(result_dir.glob("*.json")):
        if f.name in ("summary.json", "score.json") or ".attempt" in f.name:
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        results[r["id"]] = r
    return results


def build_packages(result_dir: Path) -> tuple[dict, list]:
    """정답 키와 응답을 범주별로 묶는다(prepare_scoring_packages.py 와 같은 구조)."""
    pkg = json.loads(zlib.decompress(base64.b64decode("".join(JUDGE_PACKAGE.read_text().split()))))
    private_key = json.loads(pkg["private_key.json"])
    verification = json.loads(pkg["verification.json"])
    ver_by_id = {c["id"]: c for c in verification.get("cases", [])}
    results = load_results(result_dir)
    by_cat, missing = {}, []
    for blind_id, info in private_key.items():
        r = results.get(blind_id, {})
        if r.get("success") is not True:
            missing.append(blind_id)
        by_cat.setdefault(info.get("category", "unknown"), []).append({
            "blind_id": blind_id, "app": info.get("app"), "case_id": info.get("case_id"),
            "description": info.get("description"),
            "verification": ver_by_id.get(info.get("case_id"), {}),
            "response": r.get("response", "")[:3000], "success": r.get("success"),
        })
    return by_cat, missing


def judge(llm, entry: dict) -> tuple[int, str]:
    """채점관 1회 호출. JSON 파싱 순서는 기존 스크립트와 같다(엄격 → 따옴표 치환 → score 정규식)."""
    if entry.get("success") is not True:
        return 0, "응답 없음/실패 — 판독 생략"
    prompt = JUDGE_PROMPT.format(
        description=entry.get("description", ""), app=entry.get("app", ""), case_id=entry.get("case_id", ""),
        verification=json.dumps(entry.get("verification", {}), ensure_ascii=False)[:500],
        response=entry.get("response", "")[:2500])
    try:
        raw = llm.invoke(prompt)
        text = (raw.content if isinstance(raw.content, str) else str(raw.content)).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            try:
                result = json.loads(text.replace("'", '"'))
            except json.JSONDecodeError:
                m = re.search(r'"?score"?\s*:\s*(\d)', text)
                result = {"score": int(m.group(1)), "reason": text[:100]} if m else {"score": 0, "reason": f"파싱불가: {text[:100]}"}
        return (1 if result.get("score") in (1, "1") else 0), str(result.get("reason", ""))
    except Exception as error:  # 판독 실패도 0점 + 사유로 남긴다(숨기지 않음)
        return 0, f"판독 실패: {error}"


def main() -> None:
    provider, job_id, dry_run = parse_request()
    result_dir = ROOT / "haness/apps/blind_review_20261027/results" / provider / "jobs" / job_id
    if not result_dir.is_dir():
        raise FileNotFoundError(f"result dir not found: {result_dir}")
    by_cat, missing = build_packages(result_dir)
    pkg_dir = result_dir / "scoring_packages"
    pkg_dir.mkdir(exist_ok=True)
    for cat, entries in sorted(by_cat.items()):
        (pkg_dir / f"{cat}.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    plan = {"provider": provider, "job_id": job_id, "scorer": SCORER_MODEL,
            "categories": {c: len(e) for c, e in sorted(by_cat.items())},
            "total": sum(len(e) for e in by_cat.values()), "missing_or_failed": missing}
    if dry_run:
        print(json.dumps({"dry_run": True, **plan}, ensure_ascii=False, indent=2))
        return

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    from langchain_google_genai import ChatGoogleGenerativeAI
    from pydantic import SecretStr
    key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    if not key:
        raise ValueError("Gemini credential absent")  # 키 값은 출력하지 않는다
    llm = ChatGoogleGenerativeAI(model=SCORER_MODEL, api_key=SecretStr(key), temperature=0,
                                 max_output_tokens=256, thinking_budget=0, max_retries=2, timeout=120)

    score_dir = pkg_dir / "scores"
    score_dir.mkdir(exist_ok=True)
    total, cases, by_category = 0, 0, {}
    for cat, entries in sorted(by_cat.items()):
        score_file = score_dir / f"{cat}_scores.json"
        existing = {s["blind_id"]: s for s in json.loads(score_file.read_text())} if score_file.exists() else {}
        scored = list(existing.values())
        for entry in entries:
            if entry["blind_id"] in existing:
                continue  # 이미 채점됨(재실행 시 건너뜀)
            sc, reason = judge(llm, entry)
            scored.append({"blind_id": entry["blind_id"], "case_id": entry["case_id"], "app": entry["app"],
                           "score": sc, "reason": reason})
            score_file.write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8")  # 건별 저장
            time.sleep(0.5)  # 기존과 같은 호출 간격(rate limit 방지)
        detected = sum(1 for s in scored if s["score"] == 1)
        by_category[cat] = {"detected": detected, "total": len(scored)}
        total += detected
        cases += len(scored)
    final = {"provider": provider, "job_id": job_id, "scorer": SCORER_MODEL, "total_score": total,
             "max_score": cases, "detection_rate": round(total / cases * 100, 1) if cases else 0,
             "by_category": by_category, "missing_or_failed": missing}
    (score_dir / "final_score.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
