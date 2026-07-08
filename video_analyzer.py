from pathlib import Path

import config
import utils


def extract_text_from_video(video_path: Path, max_frames: int = config.VIDEO_OCR_MAX_FRAMES) -> str:
    """비디오에서 OCR 텍스트를 추출합니다.

    구성 값 VIDEO_OCR_SECONDS_PER_SAMPLE에 따라 영상에서 일정 시간 간격으로 한 프레임씩 샘플링합니다.
    한 프레임을 추출할 때마다 OCR을 실행하고 최대 VIDEO_OCR_MAX_FRAMES개까지 수집합니다.
    """
    try:
        import cv2
        import pytesseract
    except ImportError as exc:
        utils.log_error(f"영상 OCR 라이브러리 누락 [{video_path.name}] - {exc}")
        return ""

    try:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            utils.log_error(f"비디오 열기 실패 [{video_path.name}]")
            return ""

        fps = capture.get(cv2.CAP_PROP_FPS) or 25
        # 초 단위 샘플링 간격을 프레임 단위로 계산합니다.
        sample_frame_step = max(1, int(round(fps * config.VIDEO_OCR_SECONDS_PER_SAMPLE)))

        texts = []
        frame_index = 0
        collected = 0

        while collected < max_frames:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = capture.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, lang=config.OCR_LANG)
            if text.strip():
                texts.append(text.strip())
                collected += 1

            frame_index += sample_frame_step
            if frame_index >= capture.get(cv2.CAP_PROP_FRAME_COUNT):
                break

        capture.release()
        return "\n\n---\n\n".join(texts).strip()
    except Exception as exc:
        utils.log_error(f"영상 OCR 실패 [{video_path.name}] - {exc}")
        return ""


def save_video_ocr_md(video_path: Path, text: str) -> None:
    """비디오 OCR 결과를 .md 파일로 저장합니다."""
    md_path = video_path.parent / (video_path.name + config.VIDEO_OCR_SUFFIX) # with_suffix 대신 파일명 결합 방식으로 수정
    try:
        md_path.write_text(
            f"# 영상 OCR 결과\n\n"
            f"- 원본 영상: {video_path.name}\n"
            f"- 경로: {utils.absolute_path(md_path)}\n\n"
            f"## 추출 텍스트\n\n"
            f"{(text if text else '텍스트를 찾지 못했습니다.')}",
            encoding="utf-8",
        )
        utils.log_message(f"영상 OCR 저장: {utils.absolute_path(md_path)}")
    except Exception as exc:
        utils.log_error(f"영상 OCR 저장 실패 [{video_path.name}] - {exc}")


def process(file_list: list[Path], result_base_path: Path) -> int:
    """영상 파일을 비디오 폴더로 이동하고 OCR 결과를 함께 저장합니다."""
    utils.log_message(f"[3.3단계 시작] 영상 분석기: {len(file_list)}개 파일 처리")
    count = 0

    for file_path in file_list:
        if utils.should_skip(file_path):
            continue
        if file_path.suffix.lower() not in config.VIDEO_EXTENSIONS:
            continue

        moved = utils.move_file_safe(file_path, result_base_path / config.DEFAULT_VIDEO_FOLDER)
        if moved != file_path:
            ocr_text = extract_text_from_video(moved)
            save_video_ocr_md(moved, ocr_text)
            count += 1

    utils.log_message(f"[3.3단계 완료] 영상 분석기: {count}개 파일 이동")
    return count
