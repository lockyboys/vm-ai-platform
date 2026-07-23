current task
SPS PDF·이미지 시연의 등록 DOCX 출력물 직접 미리보기·출력 연결.

completed
- Level 5 Identifier Blueprint를 HHMMSSCC / random_length=0으로 실제 DB 반영 완료.
- web/document_demo_app.py 완료 화면에 DOCX 미리보기·출력 버튼을 추가.
- /preview/<work_session_id>/docx 라우트가 현재 로그인 Session의 등록 DOCX만 읽어 브라우저 출력용 리포트 화면으로 렌더링.
- 기존 DOCX 다운로드, Markdown 실행 리포트 다운로드, 결과 화면 출력은 보존.

next task
- 웹앱 재시작 후 파일 1건 처리 → DOCX 미리보기·출력 → 브라우저 인쇄 미리보기 동작 확인.

decisions
- 결과 화면 출력과 등록 DOCX 출력물 출력은 분리한다.
- DOCX 미리보기는 Work Session에 등록된 경로만 사용하고 OUTPUT_ROOT 밖의 파일은 차단한다.
- DB 구조 변경 및 하드코딩 없음.