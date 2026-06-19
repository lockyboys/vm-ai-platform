# 📋 README_v7.md — VM Project 버전별 변경 이력

> 🆕 새로운 기능은 `🆕`, 변경은 `🔄`, 삭제는 `🗑️`, 버그수정은 `🐛` 으로 표시해요!
> 초등학생 설명: 일기처럼 "언제 뭐가 바뀌었는지" 기록해두는 파일이에요!


---

## 🐛 7.20.0 Hotfix (2026-06-16) — 화면 버전/분석 실행/학습방식 선택 수정
> 큰 틀은 그대로 두고, 기본 기능이 바로 보이고 작동하도록 고친 안전 패치입니다.

### 🐛 수정된 것
- 메인 대시보드 왼쪽 상단 배지가 더 이상 `7.16.4`로 고정 표시되지 않음
- `config.py`의 `APP_VERSION=7.20.0`이 화면 전체에 자동 반영
- `/api/run` 분석 실행 API 추가
- `/api/download/<filename>` 다운로드 API 추가
- CSV뿐 아니라 XLSX/XLS/TSV도 분석 파이프라인에서 읽도록 수정
- 엑셀 시트 선택 UI 누락 보완
- 학습방식 추천 시 버튼이 실제로 자동 선택되도록 `btn-supervised`, `btn-unsupervised`, `btn-semi`, `btn-rl` ID 추가
- 추천 메시지를 유지하면서 “자동으로 선택했어요, 원하면 바꿀 수 있어요” 안내 문구 추가
- `targetSel` 오타 수정으로 준지도학습 선택 오류 방지

### 🛡️ DB 안전 원칙
- DB 삭제 없음
- 기존 사용자/업로드/분석 이력 유지
- 마이그레이션은 `CREATE IF NOT EXISTS`, `ALTER ADD COLUMN IF NOT EXISTS` 계열만 사용

### 🧒 쉬운 설명
화면 이름표가 예전 버전으로 붙어 있던 것을 새 이름표로 바꾸고,
“AI 분석 시작” 버튼이 실제 분석 공장으로 연결되게 길을 다시 이어준 패치입니다.

---

## 🚀 7.20.0 (2026-06-16) — Enterprise 구조 안정화
> 큰 틀을 해치지 않고, 서버 자동 실행과 최종 구조도를 추가한 버전입니다.

### 🆕 새로 추가된 것
- `web/templates/mindmap_v7.20.0.html` — 최신 마인드맵
- `docs/DIRECTORY_STRUCTURE_v7.20.md` — 최종 디렉토리 구조도
- `docs/FINAL_REPORT_v7.20.md` — 최종 보고서
- `deployment/systemd/vm-project.service` — VM 부팅 시 서버 자동 실행
- `scripts/install_autorun.sh` — systemd 자동 실행 등록
- `scripts/watchdog.sh` — 서버 건강검진 후 자동 재시작
- `scripts/install_watchdog_cron.sh` — watchdog cron 등록
- `migrations/20260616_v720_safe_upgrade.sql` — DB를 지우지 않는 안전 업그레이드
- `core/automl_engine.py` — AutoML 모델 선택 골격
- `core/reinforcement_engine.py` — 강화학습 연결 골격
- `core/report_generator.py` — 리포트 생성 골격
- `core/anomaly_detector.py` — 이상값 탐지 전용 모듈

### 🛡️ DB 안전 원칙
- DB 삭제 없음
- 테이블 비우기 없음
- 기존 사용자/업로드/분석 이력 유지
- 필요한 테이블과 컬럼만 `IF NOT EXISTS` 방식으로 추가

### 🚀 서버 자동 운영
- `systemd`로 서버를 부팅 시 자동 시작
- `watchdog`가 1분마다 `/api/status`를 확인
- 서버가 응답하지 않으면 자동 재시작

### 🧒 쉬운 설명
컴퓨터가 켜지면 서버도 같이 켜지고, 서버가 잠들면 감시자가 깨워줍니다.
DB는 기존 일기장을 버리지 않고, 새 페이지를 뒤에 붙이는 방식으로 업그레이드합니다.

---

## 📌 버전 관리 규칙 (Semantic Versioning)

> 형식: **`주버전.부버전.패치버전`**  예) `7.12.0`

| 자리 | 숫자 | 언제 올리나요? | 예시 |
|---|---|---|---|
| 🔴 **주버전** | 맨 앞 `7` | 아키텍처 전면 변경, 학습방식 추가, AGI 통합 등 **크게 바뀔 때** | `7.12.0 → 8.0.0` |
| 🟡 **부버전** | 가운데 `10` | 새 기능 추가, API 추가, 권한 변경, 페이지 추가 등 **요구사항 반영** | `7.12.0 → 7.12.0` |
| 🟢 **패치버전** | 맨 뒤 `0` | 주석 수정, 가격 변경, 오타 수정, 색깔 변경 등 **자잘한 수정** | `7.12.0 → 7.12.0` |

```
초등학생 설명:
  7  . 10 . 0
  ↑    ↑    ↑
  집   방   책상
  (크게 이사) (방 추가) (책상 위치 변경)
```

> ⚠️ 버전 변경 시 `config.py`의 `APP_VERSION` 한 곳만 수정하면 전체 반영!

---

## 🚀 7.12.0 (2026-06-16) — 현재 버전
> 패치버전 업 (자잘한 수정 · 보완사항 반영)

### 🔄 변경된 것

#### ⏰ Cron 관리 — Pro에 제한적 제공
| 플랜 | 변경 전 | 변경 후 |
|---|---|---|
| 🟢 Free | ❌ 불가 | ❌ 불가 |
| 🟡 Pro | ❌ 불가 | 🔶 `Cron조회` (이력 보기만) |
| 🟣 Enterprise | ✅ `Cron관리` | ✅ `Cron조회` + `Cron관리` |

추가된 API:
- `GET /api/cron/status` — Pro 이상 Cron 실행 이력 조회
- `POST /api/cron/trigger` — Enterprise만 수동 실행

#### 🌟 준지도학습 마케팅 뱃지 추가
- `ENTERPRISE_HIGHLIGHTS` 딕셔너리 — 희귀 기능 설명/예시 등록
- UI 버튼에 "🌟 업계 희귀" 뱃지 항상 표시 (비허용 플랜에도 보임)
- 마케팅 포인트: "라벨 30%만 있어도 AI가 나머지 70% 유추 → 비용 절감"

#### 💳 업그레이드 UX 추가
- `get_upgrade_info(plan, feature)` 함수 — 업그레이드 안내 정보 반환
- 권한 없을 때 팝업 자동 표시 (플랜 선택 카드 + 결제 페이지 링크)
- 추가된 API:
  - `GET /api/upgrade-info?plan=free&feature=강화학습`
  - `GET /api/enterprise-highlights`

#### 📝 주석 전면 강화
- `agents/` 전체 파일: 클래스/함수 docstring 추가
- `core/` 전체 파일: 상세 주석 + Args/Returns 명시
- `utils.py`: 함수별 초등학생 설명 + 사용 예시 추가
- `monitoring/health_check.py`: 복구 흐름 설명 추가

---

## 🚀 7.12.0 (이전) — 

### 🆕 새로 추가된 것

#### 🌍 서버 주소 전역변수 (config.py)
- `SERVER_HOST` — IP/도메인을 한 곳에서 관리 (여기만 바꾸면 전체 반영!)
- `SERVER_BASE_URL` — 전체 주소 자동 조합 (`http://34.64.209.152:8000`)
- `SERVER_API_URL` — API 주소 자동 조합
- `set_env()` — 환경 빠른 전환 함수 (`local` / `gcp` / `production`)
- `ENV_PRESETS` — 환경별 주소 프리셋 딕셔너리

```python
# IP 바꾸는 법 — config.py 한 줄만!
SERVER_HOST = "34.64.209.152"  # ← 여기만!

# 또는 환경 전환
from config import set_env
set_env('local')       # 127.0.0.1
set_env('gcp')         # 34.64.209.152
set_env('production')  # your-domain.com
```

#### 🔐 로그인/회원가입/약관 페이지 통합
- `web/templates/login.html` — 로그인 페이지 (`/login`)
- `web/templates/register.html` — 회원가입 + 플랜선택 + 약관동의 (`/register`)
- `web/templates/terms.html` — 서비스 약관 전문 (`/terms`)
- 모든 페이지가 `SERVER_BASE_URL`을 Flask에서 자동 주입받음

#### 💰 요금제 가격 전역관리 (config.py)
```python
PLAN_PRICES = {
    "free":       0,      # 무료
    "pro":        5000,   # 월 5,000원
    "enterprise": 10000,  # 월 10,000원
}
```
- 가격 바꾸려면 `config.py`의 `PLAN_PRICES`만 수정!
- Flask가 모든 HTML 템플릿에 자동 주입 (`{{ PLAN_PRICES.pro }}`)

#### 🎯 권한 시스템 세분화
| 플랜 | 변경 내용 |
|---|---|
| 🟢 Free | `AI분석` 추가 — 단, **분류(Classification)만** 허용 |
| 🟡 Pro | `배치처리` 추가 (이전엔 Enterprise만) |
| 🟣 Enterprise | 변경 없음 (전체 유지) |

- `PARTIAL_PERMISSIONS` 딕셔너리 추가 — UI에서 🔶 주황 뱃지로 표시
- `check_learning_permission()` — 분류/회귀 구분 권한 체크 함수 추가
- `_suggest_upgrade()` — 권한 없을 때 업그레이드 플랜 안내

#### 📊 config.py 구조 전면 개선 (Smart File Organizer 참고)
- 섹션별 명확한 분리 (`# ──` 구분선)
- 초등학생도 이해할 수 있는 주석 추가
- 변경 이력 주석 (`# [변경 이력]`) 추가
- 전역 상태 변수 분리 (`LOG_QUEUE`, `LOG_LISTENER`, `ORIGINAL_STDOUT`)
- `REQUIRED_DIRS` — 자동 생성할 폴더 목록 통합 관리

#### 🎨 UI 색상 구분 (3단계)
```
✅ 녹색 — 완전 허용
🔶 주황 — 일부 허용 (Free의 AI분석: 분류만)
❌ 회색 취소선 — 사용 불가
```

#### 🏗️ 인프라 파일 추가
- `kubernetes/deployment.yaml` — K8s 배포 + HPA 오토스케일링
- `terraform/main.tf` — GCP 인프라 자동 생성

---

### 🔄 변경된 것

| 파일 | 변경 내용 |
|---|---|
| `config.py` | Smart File Organizer 구조 참고해서 전면 재작성 |
| `utils.py` | 자잘한 함수 통합 (read_csv_safe, file_hash, flatten_dict) |
| `web/app.py` | Flask jinja globals에 SERVER_BASE_URL, PLAN_PRICES 주입 |
| `web/app.py` | `/login`, `/register`, `/terms` 라우트 추가 |
| `web/app.py` | `배치처리` API (`/api/batch`) — pro 이상 허용 |
| `web/app.py` | `/api/register`, `/api/login` 엔드포인트 추가 |
| `services/auth/auth_service.py` | 플랜별 권한 세분화, 가격 정보 주석 |
| `services/db/db_service.py` | `cron_logs` 테이블 자동 생성 추가 |
| `web/templates/index.html` | `SERVER_BASE_URL`, `SERVER_API_URL` JS 전역변수 주입 |

---

### 🗑️ 삭제된 것 (구버전 대비)

| 파일/폴더 | 삭제 이유 |
|---|---|
| `agents/code_agent.py` | orchestrator.py로 통합 |
| `core/data_profiler.py` | analyzer.py 안으로 통합 |
| `ml/automl.py` | trainer.py의 `_automl_select()`로 통합 |
| `pipelines/` | 루트 `pipeline.py`로 단순화 |
| `workers/` | 빈 폴더, 미사용 |
| `services/billing/` | auth_service.py의 플랜 관리로 통합 |
| `run_auto.sh` (루트) | `scripts/run_auto.sh`로 정리 |

---

## 📦 v6.0.0 (2026-06-15)

### 주요 기능
- AGI 오케스트레이터 (멀티에이전트 시스템)
- 4가지 학습 방식 (지도/비지도/준지도/강화학습)
- AutoML 자동 모델 선택
- SHAP 시각화 자동화
- MongoDB + MariaDB 동시 저장
- Cron 자동 재학습
- Self-Healing 모니터링
- Docker + Kubernetes + GCP Terraform
- JWT 권한 시스템 (기본 버전)
- 파일 업로드/다운로드
- PDF 리포트 자동 생성

---

## 📦 v5.0.0 (이전)
- 자율 AI 운영 시스템 (Self-Healing, Auto-Scaling)
- Kafka 이벤트 스트리밍
- Vector DB 메모리 시스템

---

## 📦 v4.0.0 (이전)
- GPU Cluster AI Inference
- Triton Model Server
- Feature Store (Redis)
- MLflow Model Registry

---

## 📦 v3.0.0 (이전)
- SaaS 플랫폼 구조
- Celery 비동기 처리
- Airflow 파이프라인
- Stripe 결제 시스템

---

## 📦 v2.0.0 (이전)
- SHAP 시각화 추가
- 모델 자동 재학습
- React UI 업그레이드
- Docker 배포

---

## 📦 v1.0.0 (최초)
- 기본 Flask + MariaDB + MongoDB 구조
- 흡연 데이터 전용 분석
- 기본 파이프라인

---

## 🔜 v8.0.0 (예정)

- [ ] 그래프/시각화 전면 개선 (matplotlib → seaborn 고급 스타일)
- [ ] PDF 리포트 레이아웃 전문화
- [ ] 모바일 반응형 UI 완성
- [ ] 마인드맵 최종 보고서
- [ ] 실시간 WebSocket 분석 진행률 표시
- [ ] 사용자별 분석 히스토리 대시보드

---

> 📌 **파일 변경 시 이 문서를 반드시 업데이트해주세요!**
> 형식: `YYYY-MM-DD | 파일명 | 변경 내용 | 담당자`
