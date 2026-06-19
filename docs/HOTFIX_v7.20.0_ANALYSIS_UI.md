# 🐛 HOTFIX v7.20.0 — 분석 실행 + UI 버전 표시 수정

## 수정 요약

- 메인 화면의 `7.16.4 AGI` 고정 문구를 `{{ APP_VERSION }} AGI`로 변경했습니다.
- `/api/run` API를 추가해서 `AI 분석 시작` 버튼이 실제 파이프라인으로 연결됩니다.
- `/api/download/<filename>` API를 추가해서 PDF/차트 다운로드 흐름을 맞췄습니다.
- `pipeline.py`가 CSV뿐 아니라 XLSX/XLS/TSV도 읽도록 `read_file_auto()`를 사용하게 수정했습니다.
- 학습방식 추천 결과가 글로만 나오지 않고, 실제 버튼도 자동 선택되도록 버튼 ID를 추가했습니다.
- 엑셀 시트 선택 UI와 업로드존 내부 ID를 추가했습니다.

## DB 안전

이 패치는 DB를 삭제하지 않습니다.

- `DROP DATABASE` 없음
- `DROP TABLE` 없음
- `TRUNCATE` 없음

## 서버 적용 방법

```bash
cd ~
cp vm_project_v7.20.0_hotfix_analysis_ui.zip ~/
unzip -o vm_project_v7.20.0_hotfix_analysis_ui.zip
cd vm_project
python3 run_server.py
```

또는 기존 launcher/admin deploy 방식으로 ZIP을 올려도 됩니다.
