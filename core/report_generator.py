# core/report_generator.py ★ 7.20.0
# PDF/HTML 리포트 생성기
# 초등학생 설명: AI 분석 결과를 숙제 보고서처럼 보기 좋게 정리해요.

from pathlib import Path
from datetime import datetime
from config import OUTPUT_REPORTS_DIR
from utils import logger


def create_text_report(result: dict, filename_prefix: str = "report") -> str:
    """PDF 라이브러리가 없어도 항상 만들 수 있는 안전한 텍스트 리포트예요."""
    out_dir = Path(OUTPUT_REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    lines = ["VM Project v7.20 분석 리포트", "=" * 40]
    for k, v in result.items():
        lines.append(f"{k}: {v}")
    path.write_text("
".join(lines), encoding="utf-8")
    logger.info(f"📄 텍스트 리포트 생성: {path}")
    return str(path)
