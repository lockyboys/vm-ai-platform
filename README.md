# 🧠 VM Project 7.12.0 — AGI AI Platform

## 🆕 v7 핵심 기능
| 기능 | 설명 |
|---|---|
| 📊 범용 CSV 분석 | 어떤 CSV든 자동 분석 |
| 🎯 Feature/Target 선택 | UI에서 직접 선택 가능 |
| 🤖 4가지 학습 방식 | 지도/비지도/준지도/강화학습 |
| ⚖️ AutoML 가중치 자동계산 | AI가 최적 모델+가중치 자동 선택 |
| ⏰ Cron 자동 재학습 | 매일 새벽 2시 자동 학습 → 정확도 향상 |
| 🧠 자기개선 에이전트 | 정확도 낮으면 자동 개선 제안 |
| 📥📤 파일 업/다운로드 | CSV 업로드 + PDF/차트 다운로드 |
| 🔐 JWT 권한 시스템 | free/pro/enterprise 플랜 |
| 🗄️ DB 테이블 자동생성 | 첫 접속 시 자동 초기화 |
| 🏥 Self-Healing | 서버 죽으면 자동 복구 |

## 🚀 시작 방법

### 방법 1: 자동 시작 (권장)
```bash
chmod +x scripts/run_auto.sh
./scripts/run_auto.sh
```

### 방법 2: 수동 시작
```bash
pip install -r requirements.txt --break-system-packages
python3 run_server.py
```

### 방법 3: Docker
```bash
docker-compose up -d
```

## ⏰ Cron 자동 등록
```bash
python3 -c "from scheduler.cron_jobs import register_crontab; register_crontab()"
```

| 스케줄 | 작업 |
|---|---|
| 매일 02:00 | 4가지 학습 방식 자동 재학습 |
| 3시간마다 | 자기개선 에이전트 체크 |
| 매시간 | 시스템 상태 확인 |
| 매주 월요일 09:00 | 주간 정확도 리포트 |

## 🌐 API
| 경로 | 설명 |
|---|---|
| `GET /` | 대시보드 |
| `GET /api/status` | 서버 상태 |
| `POST /api/upload` | CSV 업로드 |
| `POST /api/run` | AI 파이프라인 실행 |
| `GET /api/download/<file>` | 결과 파일 다운로드 |
| `GET /api/files` | 다운로드 파일 목록 |
| `GET /api/history` | 모델 정확도 히스토리 |
| `GET /api/permissions?plan=pro` | 권한 확인 |

## 💰 요금제
| 플랜 | 가격 | 주요 기능 |
|---|---|---|
| 🟢 Free | 무료 | 기본분석 + CSV업로드 + **분류(classification)만** |
| 🟡 Pro | 월 5,000원 | 분류+**회귀** + 비지도학습 + SHAP + PDF + **배치처리** |
| 🟣 Enterprise | 월 10,000원 | **전부** (준지도+강화학습+AutoML+Cron관리+API접근) |
