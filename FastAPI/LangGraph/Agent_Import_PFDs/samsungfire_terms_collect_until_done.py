"""삼성화재 전체 버전 약관을 '끝까지 스스로' 받는 실행 래퍼 (2026-11-01, LuckyBoys: "어플이 스스로 받도록").

왜 래퍼인가: MCP 실행 도구는 로컬 실행에 명령줄 인자(argv)를 넘기지 못한다. 기존 batch_000 래퍼와 같이
  samsungfire_terms_pdf_collect_all_versions.main(argv) 를 직접 부른다(수집 로직 중복 없음, 원본 수정 없음).
입력(stdin JSON): {"mode": "verify" | "all"}
  verify : --verify-only — 카탈로그 조회 + 로컬 PDF 검증만(다운로드 없음) = dry-run 증빙
  all    : --limit 0 --workers 4 로 남은 항목 전부 → 이어서 --retry-errors --limit 0 으로 실패분 1회 재시도
           manifest 가 항목마다 원자 저장되므로 중간에 끊겨도 다시 실행하면 이어받는다.
"""
import json
import sys

from samsungfire_terms_pdf_collect_all_versions import OUT, catalog, main, verify_rows

mode = json.loads(sys.stdin.read() or "{}").get("mode")
if mode == "verify":
    # --verify-only 는 9,413건 목록 전체를 출력하므로, 같은 함수로 검증하고 개수만 출력한다(다운로드 없음).
    audit = verify_rows(catalog(True), OUT)
    print(json.dumps({k: audit[k] for k in ("catalog_count", "downloaded_count", "missing_count")}
                     | {"missing_sample": [m["key"] for m in audit["missing"][:5]]}, ensure_ascii=False))
    raise SystemExit(0)
if mode == "all":
    main(["--limit", "0", "--workers", "4"])  # 1차: 아직 시도하지 않은 항목 전부
    raise SystemExit(main(["--limit", "0", "--workers", "4", "--retry-errors"]))  # 2차: 실패분만 재시도
raise SystemExit("mode must be 'verify' or 'all'")  # 잘못된 입력은 아무것도 받지 않고 종료
