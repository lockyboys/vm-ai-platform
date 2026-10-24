"""첫 페이지 제목 처리의 호환 진입점. 원본 PDF는 변경하지 않는다."""
from pathlib import Path
import runpy
if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(root / "haness/aia_first_page_names.py"), run_name="__main__")
