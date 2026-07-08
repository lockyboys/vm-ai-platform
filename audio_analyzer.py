from pathlib import Path
import tempfile

import config
import utils


def convert_audio_to_wav(source_file: Path) -> Path:
    """필요한 경우 오디오를 WAV 형식으로 변환합니다."""
    if source_file.suffix.lower() == ".wav":
        return source_file

    try:
        from pydub import AudioSegment
    except ImportError:
        utils.log_error(
            f"pydub 미설치로 오디오 변환 불가 [{source_file.name}] - WAV 변환이 필요한 파일입니다."
        )
        return source_file

    try:
        # 비-WAV 오디오를 임시 WAV 파일로 변환하여 SpeechRecognition에서 읽을 수 있게 합니다.
        audio = AudioSegment.from_file(str(source_file))
        temp_file = Path(tempfile.gettempdir()) / f"{source_file.stem}_transcribe.wav"
        audio.export(str(temp_file), format="wav")
        return temp_file
    except Exception as exc:
        utils.log_error(f"오디오 변환 실패 [{source_file.name}] - {exc}")
        return source_file


def transcribe_audio_to_text(source_file: Path) -> str:
    """오디오 파일을 가능한 경우 텍스트로 변환합니다."""
    wav_file = None
    try:
        import whisper
        import torch
    except ImportError as exc:
        utils.log_error(f"Whisper 라이브러리 로드 실패 (레거시 엔진으로 전환합니다) - {exc}")
        whisper = None

    try:
        # 1. Whisper 시도 (라이브러리가 있을 경우)
        if whisper:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = whisper.load_model("base", device=device)
            result = model.transcribe(str(source_file), fp16=(device == "cuda"))
            return result["text"].strip()
            
        # 2. 백업: SpeechRecognition (Sphinx/Google)
        import speech_recognition as sr
        wav_file = convert_audio_to_wav(source_file)
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(str(wav_file)) as audio_file:
                audio_data = recognizer.record(audio_file)
            text = recognizer.recognize_sphinx(audio_data)
            utils.log_message(f"오디오 자동 인식 성공(Sphinx) [{source_file.name}]")
            return text
        except Exception as sphinx_exc:
            utils.log_error(f"오디오 Sphinx 인식 실패, Google API 시도 [{source_file.name}] - {sphinx_exc}")
            # Sphinx가 실패하면 Google Web Speech API로 재시도합니다.
            text = recognizer.recognize_google(audio_data)
            utils.log_message(f"오디오 자동 인식 성공(Google) [{source_file.name}]")
            return text
            
    except Exception as exc:
        utils.log_error(f"오디오 텍스트 변환 실패 [{source_file.name}] - {exc}")
        return ""
    finally:
        # 임시 변환된 WAV 파일 안전하게 삭제
        if wav_file and wav_file != source_file and wav_file.exists():
            try:
                wav_file.unlink()
            except OSError as exc:
                utils.log_error(f"임시 오디오 파일 삭제 실패 [{wav_file.name}] - {exc}")


def classify_audio_by_transcript(transcript: str) -> str:
    """오디오 텍스트 내용에 따라 적절한 분류 폴더를 선택합니다."""
    if not transcript:
        return config.DEFAULT_AUDIO_FOLDER

    lower_text = transcript.lower()
    for folder, keywords in config.KEYWORD_RULES.items():
        if any(keyword.lower() in lower_text for keyword in keywords):
            return folder
    # 키워드가 없으면 기본 오디오 폴더로 보냅니다.
    return config.DEFAULT_AUDIO_FOLDER


def save_transcript_md(audio_path: Path, transcript: str, destination_folder: Path) -> None:
    """오디오 파일에 대응하는 .md 텍스트 파일을 저장합니다."""
    if not transcript:
        return

    destination_folder.mkdir(parents=True, exist_ok=True)
    md_path = destination_folder / f"{audio_path.stem}{config.AUDIO_TRANSCRIPT_SUFFIX}"
    try:
        # 오디오 파일과 함께 동일 폴더에 텍스트 변환 결과를 Markdown으로 기록합니다.
        md_path.write_text(
            f"# 오디오 파일 텍스트 변환\n\n"
            f"- 원본 파일: {audio_path.name}\n"
            f"- 저장 경로: {md_path.name}\n\n"
            f"## 변환 결과\n\n"
            f"{transcript}\n",
            encoding="utf-8",
        )
        utils.log_message(f"오디오 텍스트 저장: {utils.absolute_path(md_path)}")
    except Exception as exc:
        utils.log_error(f"오디오 텍스트 저장 실패 [{audio_path.name}] - {exc}")


def process(file_list: list[Path], result_base_path: Path) -> int:
    """오디오 파일을 텍스트로 변환하고 분류 폴더로 이동합니다."""
    utils.log_message(f"[3.4단계 시작] 오디오 분석기: {len(file_list)}개 파일 처리")
    count = 0
    transcript_count = 0

    for file_path in file_list:
        if utils.should_skip(file_path):
            continue
        if file_path.suffix.lower() not in config.AUDIO_EXTENSIONS:
            continue

        transcript = transcribe_audio_to_text(file_path)
        matched_folder = classify_audio_by_transcript(transcript)
        destination_folder = result_base_path / matched_folder
        moved = utils.move_file_safe(file_path, destination_folder)

        if moved != file_path:
            count += 1
            if transcript:
                save_transcript_md(file_path, transcript, destination_folder)
                transcript_count += 1

    utils.log_message(
        f"[3.4단계 완료] 오디오 분석기: {count}개 파일 이동, {transcript_count}개 오디오 텍스트 저장"
    )
    return count
