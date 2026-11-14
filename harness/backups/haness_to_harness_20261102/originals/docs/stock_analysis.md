# 종목 분석 → 카카오페이증권 수동 주문

LuckyBoys용 SPS 분석 도구. 대상 프로젝트는 `/data/vm_project`이며 Python 3.11 이상과 기존 SPS `config.py`, `common/common_function.py`, python-dotenv를 사용합니다.

## 현재 검증 상태

- SPS 서버에서 22개 테스트 통과. 가상 예제 CLI 실행, 기본 dry-run 검증 완료.
- 실행 환경에서 KIS_APP_KEY/KIS_APP_SECRET 두 이름의 값은 읽히지 않았습니다. 다른 이름으로 저장됐거나 보호파일 접근이 제한됐는지는 미확인입니다.
- 실제 KIS 인증/시세 조회는 미실행. 공시 자동 수집, MCP 신규 도구 등록, 카카오 계좌 연결은 구현 범위에 포함하지 않았습니다.
- 주문은 카카오페이증권 앱에서 직접 합니다. API 호출은 한국투자 토큰 발급과 두 일봉 시세 경로만 허용합니다.

## 파일

- `haness/stock_analysis.py`: 조회 어댑터와 분석 함수, CLI.
- `FastAPI/LangGraph/run_stock_analysis.py`: 기존 SPS 실행 경로의 진입점.
- `config.py`: STOCK_ANALYSIS 중앙 설정 추가. 수정 전 `config_BACKUP_20261023_stock_analysis.py` 보존.
- `tests/test_stock_analysis.py`: 정상·실패·경계·명령 실행 검증.
- `examples/stock_analysis/demo.json`: 가상 데이터. 투자 추천이 아닙니다.
- `examples/stock_analysis/evidence_template.json`: 실사용 공시 근거 입력 시작점.
- `outputs/stock_analysis/runtime_dryrun.json`: 인증 값 없이 등록 여부만 남긴 실행 증거.

DB 저장은 요청 범위에 없어 연결하지 않습니다. 따라서 `common/database.py` 변경이나 MariaDB SELECT/DDL은 수행하지 않았습니다. 텍스트 필수값 검증은 기존 `common.common_function.normalize_required_text`를 재사용합니다.

## 실행

프로젝트 루트에서 기존 venv를 활성화한 후 실행합니다.

```bash
# 외부 접속 없이 시세 API 경로와 인증 등록 여부만 확인합니다.
python FastAPI/LangGraph/run_stock_analysis.py --symbol 005930 --market KR
# 배포된 가상 예제 분석 명령. 후보는 가상 데이터 결과입니다.
python FastAPI/LangGraph/run_stock_analysis.py --input examples/stock_analysis/demo.json
# 동일한 테스트를 다시 실행합니다.
python -m pytest tests/test_stock_analysis.py -q
```

## 실제 시세 연결

한국투자증권 Open API 신청으로 발급된 App Key와 App Secret을 `KIS_APP_KEY`, `KIS_APP_SECRET` 환경변수로 등록합니다. 기존 `/etc/sps-harness/secrets.env` 또는 프로젝트 `.env`에서 두 이름만 읽으며 값은 출력하지 않습니다. 채팅이나 Git에 키를 넣지 마세요. 기존 이름이 다르면 `config.py`의 `kis_app_key_env`, `kis_app_secret_env`를 실제 환경변수 이름으로 변경합니다. 이 모듈은 실전 시세 도메인을 쓰지만 주문 기능은 없습니다.

```bash
# 국내: 벤치마크는 KOSPI200 ETF 069500을 대용으로 쓰는 예시입니다.
python FastAPI/LangGraph/run_stock_analysis.py --fetch --symbol 005930 --market KR --benchmark 069500 --input examples/stock_analysis/evidence_template.json
# 미국: SPY를 S&P500 대용 벤치마크로 사용합니다.
python FastAPI/LangGraph/run_stock_analysis.py --fetch --symbol NDAQ --market US --exchange NAS --benchmark SPY --benchmark-exchange AMS --input examples/stock_analysis/evidence_template.json
```

두 live 명령은 인증 미확인으로 미실행입니다. API 권한·시세 구독·호출 제한은 실제 계좌로 확인해야 합니다. 당일 장중 데이터를 잘못 완료봉으로 사용하지 않도록 API 모드는 KST 기준 전날까지만 조회합니다. 주가 지연 및 하루 늦은 신호가 생길 수 있으며 주문 전 카카오 앱에서 재확인해야 합니다.

## 공시 근거 입력

근거 템플릿의 evidence를 다음 구조로 채웁니다. 수치는 전년 동기 대비 증가율(%)이며 PE는 배수입니다.

```json
{
  "evidence": {
    "demand_yoy": {"value": 10, "source": "https://example.com/실제-수요-공시-URL로-교체", "asof": "2026-10-01"},
    "revenue_yoy": {"value": 10, "source": "https://example.com/실제-실적-공시-URL로-교체", "asof": "2026-10-01"},
    "profit_yoy": {"value": 15, "source": "https://example.com/실제-실적-공시-URL로-교체", "asof": "2026-10-01"},
    "pe": {"value": 20, "source": "https://example.com/실제-가격평가-URL로-교체", "asof": "2026-10-01"}
  }
}
```

위 숫자와 URL은 설명용 예제이며 실제 기업 근거가 아닙니다. source는 입력자의 증빙 링크이며 프로그램은 URL 형식과 날짜만 검사합니다. 원문 내용의 진실성·회계기준·통화·일회성 이익 여부는 자동 검증하지 않습니다. 수요 지표는 물동량·판매량·수주량 등 기업에 맞는 지표를 같은 기준으로 선택하세요. PE의 저평가 기준 25배는 검증할 초기 가정이며 업종별 공정가치를 보장하지 않습니다.

## 선별 정의

1. 수요 증가율 >0, 매출·이익 증가율 모두 >0.
2. 0<PE<=25. 근거 기준일이 미래이거나 120일 초과이면 미확인.
3. 최근 30거래일 수익률이 벤치마크보다 높음. 종목과 벤치마크 날짜는 정확히 일치해야 함.
4. 돌파 전 5일 최저가가 그 기간 최고가의 90% 이상이고 직전 종가가 20일 평균 이상.
5. 현재 종가가 직전 20일 최고가를 초과하고 거래량이 직전 20일 평균의 1.5배 이상. 오늘 데이터는 기준선 계산에서 제외.
6. 마지막 데이터가 분석 기준일보다 7일 이상 오래됐으면 미확인. 데이터가 없거나 근거 누락이면 후보로 처리하지 않음.

이는 시간상 인과관계를 입증한 모델이나 수익률을 검증한 전략이 아닙니다. 상태는 후보/대기/미확인이며 자동 매수 신호로 주문하지 않습니다. 한 종목씩 분석하고 JSON 결과의 checks와 metrics를 검토한 뒤 카카오 앱에서 수동 주문합니다.

## 공식 API 계약 근거

- https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_daily_itemchartprice/inquire_daily_itemchartprice.py
- https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/dailyprice/dailyprice.py

개별 API 계약은 확인했으며 실제 계좌의 응답은 미확인입니다. 서비스 재시작과 Git 커밋은 수행하지 않았습니다.
