"""조회 전용 종목 선별: 결측을 합격 처리하지 않고 당일 봉을 기준선에서 제외한다."""
import copy
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys
import pytest

# 원격 SPS와 독립 다운로드 패키지에서 동일한 모듈을 검증한다.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from haness.stock_analysis import analyze, KisMarketData, parse_bars, run_plan


def sample():
    """상승 이후 5일 가격유지, 마지막 날 거래량 돌파를 갖는 가상 데이터."""
    start = date(2026, 8, 1)
    bars = []
    for i in range(40):
        close = 100 + min(i, 34) * .5
        bars.append(dict(date=str(start + timedelta(days=i)), close=close,
                         high=close + 1, low=close - 1, volume=1000))
    bars[-1].update(close=120, high=121, low=117, volume=2000)
    evidence = {k: dict(value=20, source="https://example.com/filing", asof=bars[-1]['date'])
                for k in ('demand_yoy', 'revenue_yoy', 'profit_yoy')}
    evidence['pe'] = dict(value=15, source="https://example.com/valuation", asof=bars[-1]['date'])
    return dict(symbol='TEST', market='US', asof=bars[-1]['date'], bars=bars,
                benchmark=[dict(x, close=100, high=101, low=99) for x in bars], evidence=evidence)


def test_candidate_and_no_order():
    result = analyze(sample())
    assert result['status'] == '후보'
    assert result['execution'] == '카카오페이증권 앱에서 직접 확인·주문'
    assert result['metrics']['volume_ratio'] == 2


def test_unknown_is_not_pass():
    data = sample(); data['evidence'] = {}
    result = analyze(data)
    assert result['status'] == '미확인'
    assert result['checks']['demand'] is None


def test_volume_excludes_current_bar():
    data = sample(); data['bars'][-1]['volume'] = 1500
    assert analyze(data)['checks']['breakout'] is True


def test_no_volume_breakout():
    data = sample(); data['bars'][-1]['volume'] = 1000
    assert analyze(data)['status'] == '대기'


def test_benchmark_dates_must_match():
    data = sample(); data['benchmark'].pop(10)
    with pytest.raises(ValueError): analyze(data)


@pytest.mark.parametrize('mutation', ['duplicate', 'nan', 'zero', 'future', 'unordered', 'short'])
def test_invalid_inputs(mutation):
    data = sample()
    if mutation == 'duplicate': data['bars'][-1]['date'] = data['bars'][-2]['date']
    if mutation == 'nan': data['bars'][0]['close'] = float('nan')
    if mutation == 'zero': data['bars'][0]['close'] = 0
    if mutation == 'future': data['bars'][-1]['date'] = '2099-01-01'
    if mutation == 'unordered': data['bars'].reverse()
    if mutation == 'short': data['bars'] = data['bars'][:10]
    with pytest.raises(ValueError): analyze(data)


def test_stale_bars():
    data = sample(); data['asof'] = '2026-10-23'
    assert analyze(data)['status'] == '미확인'


def test_future_evidence_unknown():
    data = sample(); data['evidence']['demand_yoy']['asof'] = '2099-01-01'
    assert analyze(data)['checks']['demand'] is None


def test_bad_ohlc():
    data = sample(); data['bars'][-1]['low'] = 130
    with pytest.raises(ValueError): analyze(data)


def test_dry_run_has_no_network():
    assert run_plan('005930', 'KR', dry_run=True)['network_called'] is False


def test_missing_credentials_blocks_network():
    client = KisMarketData(app_key='', app_secret='')
    with pytest.raises(ValueError, match='인증'): client.bars('005930', 'KR', '2026-10-23')


def test_only_marketdata_routes():
    client = KisMarketData(app_key='test', app_secret='test')
    with pytest.raises(ValueError): client._request('GET', '/uapi/trading/order', {}, '')


def test_korean_response_normalized():
    bars = parse_bars([dict(stck_bsop_date='20261022', stck_clpr='100', stck_hgpr='101', stck_lwpr='99', acml_vol='50')], 'KR')
    assert bars[0]['date'] == '2026-10-22'
    assert bars[0]['volume'] == 50


def test_api_errors_do_not_leak_credentials(monkeypatch):
    import haness.stock_analysis as module
    client = KisMarketData(app_key='SECRETKEY', app_secret='SECRETSECRET')
    def fail(*a, **k): raise RuntimeError('SECRETKEY SECRETSECRET')
    monkeypatch.setattr(module.urllib.request, 'urlopen', fail)
    with pytest.raises(RuntimeError) as error: client._token()
    assert 'SECRET' not in str(error.value)


def test_cli_dry_run_and_runtime_evidence():
    """실제 서버 환경의 CLI 실행 증거를 남깁니다. 인증 값 대신 등록 여부만 기록합니다."""
    import json
    import subprocess
    report = subprocess.run([sys.executable, str(ROOT/'FastAPI/LangGraph/run_stock_analysis.py')],
                            cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert report.returncode == 0, 'CLI 실행 실패(비밀 보호를 위해 stderr 생략)'
    data = json.loads(report.stdout)
    assert data['orders_enabled'] is False and data['network_called'] is False
    assert all(isinstance(value, bool) for value in data['credentials'].values())
    destination = ROOT/'outputs/stock_analysis/runtime_dryrun.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def test_us_marketdata_request(monkeypatch):
    """미국 조회 요청·수정주가 파라미터·당일 제외를 공식 계약과 대조합니다."""
    client = KisMarketData(app_key='test', app_secret='test')
    requests = []
    start = date(2026, 8, 1)
    def response(method, path, params, tr_id):
        requests.append((method, path, params, tr_id))
        return {'output2':[dict(xymd=(start+timedelta(days=i)).strftime('%Y%m%d'),
                                clos='100', high='101', low='99', tvol='500') for i in range(40)]}
    monkeypatch.setattr(client, '_request', response)
    result = client.bars('SPY', 'US', '2026-10-22', 'AMS')
    assert len(result) == 31
    assert requests[0][2]['MODP'] == '1'
    assert requests[0][2]['EXCD'] == 'AMS'
    assert requests[0][3] == 'HHDFS76240000'


def test_demo_command():
    """배포하는 예제 명령을 실제 CLI에서 실행하고 가상 데이터 표시를 보존합니다."""
    import json
    import subprocess
    report = subprocess.run([sys.executable, str(ROOT/'FastAPI/LangGraph/run_stock_analysis.py'),
                             '--input', 'examples/stock_analysis/demo.json'], cwd=ROOT,
                            capture_output=True, text=True, timeout=20)
    assert report.returncode == 0, '예제 명령 실행 실패'
    data = json.loads(report.stdout)
    assert data['status'] == '후보'
    assert '가상 예제' in data['data_mode']
