# 🧭 VM Project v7.20.0 디렉토리 구조도

> 초등학생 설명: 프로젝트를 하나의 학교라고 생각하면, 각 디렉토리는 교실이에요.  
> DB는 지우지 않고, 필요한 교실만 추가했습니다.

```text
vm_project/
├── agents/                    # AI 에이전트 교실: 계획, 기억, 추론, 자기개선
├── core/                      # AI 핵심 교실: 분석, AutoML, SHAP, 리포트, 강화학습
│   ├── automl_engine.py        # 여러 모델을 시험해서 최고 모델을 고르는 곳
│   ├── reinforcement_engine.py # 강화학습 연결 준비 공간
│   ├── report_generator.py     # 리포트를 만드는 곳
│   └── anomaly_detector.py     # 튀는 숫자를 찾는 곳
├── services/                  # 외부 도구 연결 교실: DB, 인증, 리포트, 저장소
│   └── db/
│       └── safe_upgrade.py     # DB를 지우지 않고 안전하게 칸만 추가
├── web/                       # 화면과 API 교실: Flask 서버와 HTML
│   └── templates/
│       ├── mindmap_v7.20.0.html
│       ├── demo_v7_reference.html
│       └── terms_v7_reference.html
├── deployment/                # 서버 자동 실행/배포 교실
│   ├── systemd/vm-project.service
│   └── cron/vm_project_watchdog.cron
├── scripts/                   # 실행 버튼 모음
│   ├── install_autorun.sh      # 서버 부팅 자동 실행 등록
│   ├── install_watchdog_cron.sh# 서버 감시 cron 등록
│   └── watchdog.sh             # 서버가 죽었는지 확인하고 재시작
├── migrations/                # DB 안전 업그레이드 SQL
├── docs/                      # 최종 보고서와 구조도
├── data/                      # 기본 데이터
├── uploads/                   # 업로드 파일
├── outputs/                   # 리포트/차트 결과
├── README_v7.md               # 버전 히스토리
└── run_server.py              # 서버 시작 파일
```

## 서버 자동 실행 구조

```text
VM 부팅
  ↓
systemd: vm-project@사용자.service 실행
  ↓
python3 run_server.py 시작
  ↓
/api/status 정상 확인
  ↓
watchdog cron이 1분마다 건강검진
  ↓
응답 없으면 systemd 재시작
```

## DB 안전 원칙

```text
DROP DATABASE 없음
TRUNCATE 없음
기존 users / logs / uploads 유지
새 테이블은 CREATE TABLE IF NOT EXISTS
새 컬럼은 ALTER TABLE ADD COLUMN IF NOT EXISTS
```
