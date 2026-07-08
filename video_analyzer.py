from pathlib import Path
import json
import time
import cv2
import easyocr


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def analyze_video(file_path: str) -> dict:
    started = time.time()
    video_path = Path(file_path)

    if not video_path.exists():
        return {"status": "FAILED", "reason": "Video file not found", "file_path": str(video_path)}

    if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
        return {"status": "FAILED", "reason": f"Unsupported video extension: {video_path.suffix}"}

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {"status": "FAILED", "reason": "Failed to open video file", "file_path": str(video_path)}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_seconds = round(frame_count / fps, 2) if fps else 0

    max_sample_frames = 80
    sample_seconds = 0.5
    sample_frame_step = max(1, int(round(fps * sample_seconds)))

    frame_dir = Path("uploads/video_frames")
    frame_dir.mkdir(parents=True, exist_ok=True)

    reader = easyocr.Reader(["ko", "en"], gpu=False)

    sampled_frames = []
    extracted_texts = []

    frame_index = 0
    sampled_count = 0

    while sampled_count < max_sample_frames:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % sample_frame_step == 0:
            second = round(frame_index / fps, 2)

            saved_frame_path = frame_dir / f"{video_path.stem}_frame_{frame_index:06d}.jpg"
            cv2.imwrite(str(saved_frame_path), frame)

            # OCR-friendly preprocessing
            ocr_frame = cv2.resize(frame, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

            ocr_results = reader.readtext(ocr_frame, detail=1, paragraph=False)

            frame_texts = []
            confidence_values = []

            for bbox, text, confidence in ocr_results:
                cleaned = text.strip()
                if cleaned:
                    frame_texts.append(cleaned)
                    confidence_values.append(float(confidence))

            frame_text = "\n".join(frame_texts).strip()
            avg_confidence = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0

            sampled_frames.append({
                "frame_index": frame_index,
                "second": second,
                "saved_frame_path": str(saved_frame_path),
                "text_length": len(frame_text),
                "confidence_avg": avg_confidence,
                "text": frame_text,
            })

            if frame_text:
                extracted_texts.append(f"[{second}s / frame {frame_index}]\n{frame_text}")

            sampled_count += 1

        frame_index += 1

    cap.release()

    full_text = "\n\n".join(extracted_texts).strip()
    if not full_text:
        full_text = "No text extracted from sampled video frames."

    result = {
        "status": "SUCCESS",
        "analyzer_module": "video_analyzer",
        "analyzer_method": "analyze_video",
        "file_path": str(video_path),
        "video_metadata": {
            "file_name": video_path.name,
            "extension": video_path.suffix.lower(),
            "file_size": video_path.stat().st_size,
            "fps": fps,
            "frame_count": frame_count,
            "duration_seconds": duration_seconds,
            "width": width,
            "height": height,
        },
        "sampling_policy": {
            "max_sample_frames": max_sample_frames,
            "sample_seconds": sample_seconds,
            "sample_frame_step": sample_frame_step,
            "ocr_engine": "EasyOCR",
            "ocr_languages": ["ko", "en"],
            "gpu": False,
        },
        "frame_analysis": {
            "sampled_count": len(sampled_frames),
            "frames": sampled_frames,
        },
        "text": full_text,
        "statistics": {
            "text_length": len(full_text),
            "elapsed_ms": int((time.time() - started) * 1000),
        },
    }

    sidecar_path = video_path.parent / f"{video_path.stem}.video_analysis.json"
    sidecar_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["sidecar_json_path"] = str(sidecar_path)

    return result


def extract_text_from_video(video_path: Path, max_frames: int = 30) -> str:
    result = analyze_video(str(video_path))
    return result.get("text", "")
