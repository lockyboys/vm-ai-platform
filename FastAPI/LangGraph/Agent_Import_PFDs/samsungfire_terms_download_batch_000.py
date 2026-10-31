"""삼성화재 약관 10건 배치 실행 래퍼."""
import sys
from samsungfire_terms_downloader import main

if __name__ == "__main__":
    sys.argv = [
        "samsungfire_terms_downloader.py", "--apply",
        "--limit", "10", "--offset", "0",
        "--output-dir",
        "/data/vm_project/outputs/insurance_docs/samsung_fire_terms_batch_000",
    ]
    raise SystemExit(main())
