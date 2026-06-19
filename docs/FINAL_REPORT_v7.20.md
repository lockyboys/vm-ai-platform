# ✅ VM Project v7.20.0 최종 보고

## 핵심 결론

v7.16.4 원본 구조를 해치지 않고 v7.20.0 Enterprise 골격을 추가했습니다.
기존 DB를 날리는 작업은 넣지 않았습니다.

## 반영 항목

- 🧭 마인드맵 v7.20.0 업데이트
- 🗂️ 디렉토리 구조도 작성
- 🛡️ DB 안전 업그레이드 SQL 추가
- 🚀 서버 자동 실행 systemd 구성 추가
- 🏥 watchdog 자동 감시 추가
- 🤖 AutoML 엔진 골격 추가
- 🎮 강화학습 엔진 연결 골격 추가
- 📄 리포트 생성 골격 추가
- 📝 README_v7.md 히스토리 추가

## DB 보존 정책

기존 데이터 보존을 최우선으로 했습니다.
`DROP`, `TRUNCATE` 명령은 추가하지 않았습니다.

## 운영 명령어

```bash
# 서버 자동 실행 등록
chmod +x scripts/install_autorun.sh
./scripts/install_autorun.sh

# 서버 감시 cron 등록
chmod +x scripts/install_watchdog_cron.sh
./scripts/install_watchdog_cron.sh

# 상태 확인
curl http://127.0.0.1:8000/api/status

# 로그 확인
tail -f logs/flask.log
```

---

## 🐛 v7.20.0 Hotfix 반영 사항

- 메인 대시보드 버전 표시를 `config.py` 기준으로 통일했습니다.
- 분석 실행 API `/api/run`을 추가했습니다.
- 다운로드 API `/api/download/<filename>`을 추가했습니다.
- CSV/XLSX/XLS/TSV 파일이 분석 파이프라인에서도 동일하게 읽히도록 수정했습니다.
- 학습방식 추천 결과가 버튼 선택 상태에 반영되도록 수정했습니다.
- 마인드맵에 분석 실행 API와 학습방식 자동 선택 항목을 반영했습니다.
- DB 삭제 없이 안전 업그레이드 원칙을 유지했습니다.
