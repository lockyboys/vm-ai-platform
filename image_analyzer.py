from pathlib import Path

import config
import utils


def classify_by_filename(file_path: Path) -> str:
    """이미지 파일명을 보고 자연/도시/인물 계열 폴더를 선택합니다."""
    lower_name = file_path.name.lower()
    for folder, keywords in config.FILENAME_ROOM_RULES.items():
        if any(keyword.lower() in lower_name for keyword in keywords):
            return folder
    return config.DEFAULT_IMAGE_FOLDER


def extract_text_from_image(image_path: Path) -> str:
    """이미지에서 OCR 텍스트를 추출합니다."""
    try:
        import easyocr
        import torch
    except ImportError as exc:
        utils.log_message("EasyOCR 미설치 - 레거시 Tesseract를 사용합니다.")
        easyocr = None

    try:
        # 한글 경로 대응: numpy로 파일을 읽은 후 cv2로 디코딩합니다.
        import numpy as np
        import cv2
        img_array = np.fromfile(str(image_path), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("이미지를 로드할 수 없습니다. (경로 인코딩 또는 파일 손상)")

        if easyocr:
            gpu_flag = torch.cuda.is_available()
            reader = easyocr.Reader(['ko', 'en'], gpu=gpu_flag)
            result = reader.readtext(img, detail=0)
            return " ".join(result).strip()
        
        # 백업용 Tesseract
        from PIL import Image
        import pytesseract
        with Image.open(str(image_path)) as image:
            return pytesseract.image_to_string(image, lang=config.OCR_LANG).strip()
    except Exception as exc:
        utils.log_error(f"이미지 OCR 실패 [{image_path.name}] - {exc}")
        return ""


def save_image_ocr_md(image_path: Path, text: str) -> None:
    """이미지 OCR 결과를 .md 파일로 저장합니다."""
    md_path = image_path.parent / (image_path.name + config.IMAGE_OCR_SUFFIX) # with_suffix 대신 파일명 결합 방식으로 수정
    try:
        # 원본 이미지와 함께 동일한 폴더에 OCR 결과 Markdown을 작성합니다.
        md_path.write_text(
            f"# 이미지 OCR 결과\n\n"
            f"- 원본 이미지: {image_path.name}\n"
            f"- 경로: {utils.absolute_path(md_path)}\n\n"
            f"## 추출 텍스트\n\n"
            f"{(text if text else '텍스트를 찾지 못했습니다.')}",
            encoding="utf-8",
        )
        utils.log_message(f"이미지 OCR 저장: {utils.absolute_path(md_path)}")
    except Exception as exc:
        utils.log_error(f"이미지 OCR 저장 실패 [{image_path.name}] - {exc}")


def append_image_classification_summary(
    source_path: Path,
    matched_folder: str,
    result_base_path: Path,
) -> None:
    """이미지 분류 결과를 요약 .md 파일로 저장합니다."""
    summary_path = result_base_path / config.DEFAULT_IMAGE_FOLDER / config.IMAGE_CLASSIFICATION_SUMMARY_FILENAME
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        f"- {source_path.name}: {matched_folder}\n"
    )
    try:
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(text)
    except Exception as exc:
        utils.log_error(f"이미지 분류 요약 저장 실패 [{source_path.name}] - {exc}")


def process(image_pool: list[Path], result_base_path: Path) -> int:
    """이미지 파일을 파일명 규칙에 따라 분류 폴더로 이동하고 OCR 결과를 함께 저장합니다."""
    utils.log_message(f"[3.2단계 시작] 이미지 분석기: {len(image_pool)}개 파일 처리")
    count = 0

    summary_header = result_base_path / config.DEFAULT_IMAGE_FOLDER / config.IMAGE_CLASSIFICATION_SUMMARY_FILENAME
    if summary_header.exists():
        try:
            summary_header.unlink()
        except OSError as exc:
            utils.log_error(f"기존 이미지 요약 파일 삭제 실패 - {exc}")

    for file_path in image_pool:
        if utils.should_skip(file_path):
            continue
        if file_path.suffix.lower() not in config.IMAGE_EXTENSIONS:
            continue

        matched_folder = classify_by_filename(file_path)
        moved = utils.move_file_safe(file_path, result_base_path / matched_folder)
        if moved != file_path:
            append_image_classification_summary(file_path, matched_folder, result_base_path)
            ocr_text = extract_text_from_image(moved)
            save_image_ocr_md(moved, ocr_text)
            count += 1

    utils.log_message(f"[3.2단계 완료] 이미지 분석기: {count}개 파일 이동")
    return count
