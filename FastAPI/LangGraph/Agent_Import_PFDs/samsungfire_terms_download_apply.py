"""승인된 삼성화재 약관 전체 다운로드 실행 래퍼.

원본 다운로더의 dry-run 결과(320건)를 확인한 뒤에만 호출한다.
MongoDB 적재는 수행하지 않는다.
"""
import sys
from samsungfire_terms_downloader import main

if __name__ == "__main__":
    sys.argv = [
        "samsungfire_terms_downloader.py",
        "--apply",
        "--output-dir",
        "/data/vm_project/outputs/insurance_docs/samsung_fire_terms",
    ]
    raise SystemExit(main())
