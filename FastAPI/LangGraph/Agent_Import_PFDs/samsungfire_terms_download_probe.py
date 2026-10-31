"""삼성화재 약관 1건 실행 검증 래퍼.
전체 실행 전 공식 PDF 다운로드 경로와 저장 구조를 검증한다.
"""
import sys
from samsungfire_terms_downloader import main

if __name__ == "__main__":
    sys.argv = [
        "samsungfire_terms_downloader.py",
        "--apply",
        "--limit", "1",
        "--output-dir",
        "/data/vm_project/outputs/insurance_docs/samsung_fire_terms_probe",
    ]
    raise SystemExit(main())
