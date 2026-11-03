"""한국투자 시세로 선별하고 카카오페이증권에서 수동 주문하는 조회 전용 도구.

수요/실적/밸류에이션은 출처와 기준일이 있는 입력 근거로 검증합니다.
이 모듈은 주문·계좌변경·DB 쓰기 기능을 제공하지 않습니다.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.request
import urllib.parse
from zoneinfo import ZoneInfo

from config import STOCK_ANALYSIS as SETTINGS
from common.common_function import normalize_required_text


def _number(value, positive=False):
    """NaN/무한대/부울을 수치로 잘못 받아들이지 않습니다."""
    if isinstance(value, bool):
        raise ValueError('부울은 수치가 아닙니다')
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError('유한한 양수 가격이 필요합니다')
    return result


def _bars(rows, asof):
    """완료 일봉만 입력하며, 날짜 역전·중복·잘못된 OHLC는 거부합니다."""
    if not isinstance(rows, list) or len(rows) < SETTINGS['lookback'] + 1:
        raise ValueError('일봉이 부족합니다')
    result = []
    for row in rows:
        day = date.fromisoformat(row['date'])
        values = {k: _number(row[k], positive=k != 'volume')
                  for k in ('close', 'high', 'low', 'volume')}
        if day > asof or (result and day <= result[-1]['day']):
            raise ValueError('미래/중복/역순 날짜')
        if values['volume'] < 0 or not values['low'] <= values['close'] <= values['high']:
            raise ValueError('잘못된 OHLC/거래량')
        result.append(dict(day=day, **values))
    return result


def analyze(payload):
    """다섯 연결 조건과 저평가 조건을 계산합니다. 결측은 None(미확인)입니다."""
    symbol = normalize_required_text(payload['symbol'], 'symbol')
    market = payload['market']
    if market not in ('KR', 'US'):
        raise ValueError('market은 KR 또는 US')
    asof = date.fromisoformat(payload['asof'])
    bars = _bars(payload['bars'], asof)
    benchmark = _bars(payload['benchmark'], asof)
    # 같은 거래일로 비교해야 휴장 차이를 상대강도로 오인하지 않습니다.
    if [b['day'] for b in bars] != [b['day'] for b in benchmark]:
        raise ValueError('종목과 벤치마크 거래일이 다릅니다')
    last, previous = bars[-1], bars[:-1]
    evidence = payload.get('evidence', {})

    def observed(key):
        """값·문서 URL·발표 기준일을 갖춘 근거만 사용합니다."""
        entry = evidence.get(key, {})
        try:
            day = date.fromisoformat(entry['asof'])
            url = urllib.parse.urlsplit(entry['source'])
            if url.scheme not in ('https', 'http') or not url.netloc:
                return None
            if not 0 <= (asof - day).days <= SETTINGS['evidence_stale_days']:
                return None
            return _number(entry['value'])
        except (KeyError, TypeError, ValueError):
            return None

    demand, revenue, profit, pe = [observed(k) for k in ('demand_yoy', 'revenue_yoy', 'profit_yoy', 'pe')]
    window = SETTINGS['lookback']
    strength = last['close'] / bars[-window-1]['close'] - benchmark[-1]['close'] / benchmark[-window-1]['close']
    base = previous[-SETTINGS['base_days']:]
    resistance = max(b['high'] for b in previous[-SETTINGS['breakout_days']:])
    avg_volume = sum(b['volume'] for b in previous[-SETTINGS['breakout_days']:]) / SETTINGS['breakout_days']
    ratio = last['volume'] / avg_volume if avg_volume > 0 else None
    # 조정 유지: 직전 5일 저가가 고가 대비 10% 이내이고 종가가 직전20일 평균 위.
    base_high = max(b['high'] for b in base)
    base_low = min(b['low'] for b in base)
    sma = sum(b['close'] for b in previous[-20:]) / 20
    checks = dict(
        demand=None if demand is None else demand > 0,
        earnings=None if revenue is None or profit is None else revenue > 0 and profit > 0,
        value=None if pe is None else 0 < pe <= SETTINGS['max_pe'],
        relative_strength=strength > 0,
        holding=base_low >= base_high * (1-SETTINGS['max_drawdown']) and base[-1]['close'] >= sma,
        breakout=None if ratio is None else last['close'] > resistance and ratio >= SETTINGS['volume_multiple'],
        fresh=(asof - last['day']).days <= SETTINGS['stale_days'],
    )
    # 데이터가 없거나 오래되면 조건 실패보다 우선하여 미확인으로 표시합니다.
    status = '후보' if all(v is True for v in checks.values()) else '대기'
    if None in checks.values() or not checks['fresh']:
        status = '미확인'
    return dict(symbol=symbol, market=market, asof=str(asof), price_date=str(last['day']),
                status=status, checks=checks, evidence=evidence,
                metrics=dict(close=last['close'], resistance=resistance,
                             volume_ratio=ratio, relative_return_pp=strength*100),
                execution='카카오페이증권 앱에서 직접 확인·주문',
                data_mode=payload.get('data_mode', '입력 데이터'),
                note='미검증 투자 가설에 따른 선별 결과이며 수익성 백테스트 결과가 아닙니다')


def parse_bars(rows, market):
    """KIS 응답을 동일한 수정주가 일봉 형식으로 바꾸고 겹치는 페이지는 병합합니다."""
    fields = ('stck_bsop_date', 'stck_clpr', 'stck_hgpr', 'stck_lwpr', 'acml_vol') if market == 'KR' else ('xymd', 'clos', 'high', 'low', 'tvol')
    parsed = {}
    for row in rows:
        day = datetime.strptime(row[fields[0]], '%Y%m%d').date().isoformat()
        item = dict(date=day, **{key: _number(row[field]) for key, field in zip(('close','high','low','volume'), fields[1:])})
        if day in parsed and parsed[day] != item:
            raise ValueError('페이지 간 일봉 값 충돌')
        parsed[day] = item
    return [parsed[day] for day in sorted(parsed)]


class KisMarketData:
    """고정된 공식 도메인·시세 경로만 호출합니다. 비밀은 메모리에만 보관합니다."""
    def __init__(self, app_key=None, app_secret=None):
        self.app_key = os.getenv(SETTINGS['kis_app_key_env'], '') if app_key is None else app_key
        self.app_secret = os.getenv(SETTINGS['kis_app_secret_env'], '') if app_secret is None else app_secret
        self.token = None
        self.last_request = 0.0

    def _io(self, request):
        # 호출 속도와 timeout을 제한하며 원본 예외의 키/요청 본문은 노출하지 않습니다.
        time.sleep(max(0, SETTINGS['request_interval']-(time.monotonic()-self.last_request)))
        try:
            with urllib.request.urlopen(request, timeout=SETTINGS['timeout']) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                raise ValueError('bad response')
            return data
        except Exception:
            raise RuntimeError('한국투자 API 연결/응답 실패; 인증과 API 권한을 확인하세요') from None
        finally:
            self.last_request = time.monotonic()

    def _token(self):
        if not self.app_key or not self.app_secret:
            raise ValueError('한국투자 인증 설정 미확인: KIS_APP_KEY/KIS_APP_SECRET')
        body = json.dumps(dict(grant_type='client_credentials', appkey=self.app_key, appsecret=self.app_secret)).encode()
        data = self._io(urllib.request.Request(SETTINGS['kis_base_url']+'/oauth2/tokenP', data=body,
                                             headers={'Content-Type':'application/json'}, method='POST'))
        token = data.get('access_token')
        if not isinstance(token, str) or not token:
            raise RuntimeError('한국투자 토큰 발급 실패')
        self.token = token

    def _request(self, method, path, params, tr_id):
        # 범용 주문 프록시가 되지 않도록 경로뿐 아니라 TR ID까지 대조합니다.
        if method != 'GET' or (path, tr_id) not in SETTINGS['kis_routes'].values():
            raise ValueError('조회 전용 시세 경로만 허용합니다')
        if not self.token:
            self._token()
        url = SETTINGS['kis_base_url'] + path + '?' + urllib.parse.urlencode(params)
        headers = dict(authorization='Bearer '+self.token, appkey=self.app_key,
                       appsecret=self.app_secret, tr_id=tr_id, custtype='P')
        data = self._io(urllib.request.Request(url, headers=headers, method='GET'))
        if data.get('rt_cd') != '0':
            raise RuntimeError('한국투자 시세 조회 실패; API 권한/호출 제한을 확인하세요')
        return data

    def bars(self, symbol, market, asof, exchange='NAS'):
        """최근 완료 일봉 31개를 확보합니다. 부족하면 분석 단계에서 미완료로 처리합니다."""
        run_plan(symbol, market, dry_run=True, exchange=exchange)
        end = date.fromisoformat(asof)
        # 당일 장중 봉과 미래 데이터는 요청하지 않습니다. 최신 완료 여부는 별도 확인 필요.
        end = min(end, datetime.now(ZoneInfo('Asia/Seoul')).date()-timedelta(days=1))
        rows = []
        for _ in range(SETTINGS['max_pages']):
            if market == 'KR':
                params = dict(FID_COND_MRKT_DIV_CODE='J', FID_INPUT_ISCD=symbol,
                              FID_INPUT_DATE_1=str(end-timedelta(days=180)).replace('-',''),
                              FID_INPUT_DATE_2=end.strftime('%Y%m%d'), FID_PERIOD_DIV_CODE='D', FID_ORG_ADJ_PRC='0')
            else:
                params = dict(AUTH='', EXCD=exchange, SYMB=symbol, GUBN='0', BYMD=end.strftime('%Y%m%d'), MODP='1')
            page = self._request('GET', *[SETTINGS['kis_routes'][market][0], params, SETTINGS['kis_routes'][market][1]]).get('output2', [])
            if not page:
                break
            rows.extend(page)
            parsed = parse_bars(rows, market)
            if len(parsed) >= SETTINGS['lookback'] + 1:
                return parsed[-SETTINGS['lookback']-1:]
            new_end = date.fromisoformat(parsed[0]['date'])-timedelta(days=1)
            if new_end >= end:
                break
            end = new_end
        return parse_bars(rows, market)


def run_plan(symbol, market, dry_run=True, exchange='NAS'):
    """키 값을 출력하지 않고 필요한 인증 등록 유무와 고정 조회 경로만 알려줍니다."""
    if market not in ('KR', 'US') or not isinstance(symbol, str):
        raise ValueError('종목/시장 입력 오류')
    if not re.fullmatch(r'\d{6}' if market == 'KR' else r'[A-Z][A-Z0-9.\-]{0,14}', symbol):
        raise ValueError('종목코드 형식 오류')
    if exchange not in ('NAS','NYS','AMS'):
        raise ValueError('미국 거래소는 NAS/NYS/AMS')
    return dict(symbol=symbol, market=market, dry_run=dry_run, network_called=False,
                credentials={name: bool(os.getenv(name)) for name in
                             (SETTINGS['kis_app_key_env'],SETTINGS['kis_app_secret_env'])},
                endpoint=SETTINGS['kis_routes'][market][0], orders_enabled=False)


def main():
    """오프라인 JSON 분석 또는 명시적 --fetch로만 외부 시세를 조회합니다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', help='근거·일봉이 담긴 JSON 파일')
    parser.add_argument('--symbol'); parser.add_argument('--market', choices=['KR','US'])
    parser.add_argument('--exchange', default='NAS'); parser.add_argument('--benchmark')
    parser.add_argument('--benchmark-exchange', default='AMS')
    parser.add_argument('--asof', default=datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat())
    parser.add_argument('--fetch', action='store_true', help='한국투자 시세 API 조회. 기본은 dry-run')
    args = parser.parse_args()
    try:
        payload = json.loads(Path(args.input).read_text(encoding='utf-8')) if args.input else None
        if args.fetch:
            if not payload or not args.symbol or not args.market or not args.benchmark:
                raise ValueError('--fetch에는 --input 근거, --symbol, --market, --benchmark 필요')
            client = KisMarketData()
            stock = client.bars(args.symbol, args.market, args.asof, args.exchange)
            bench = client.bars(args.benchmark, args.market, args.asof, args.benchmark_exchange)
            payload.update(symbol=args.symbol, market=args.market, asof=args.asof, bars=stock,
                           benchmark=bench, data_mode='KIS 일봉 조회; 당일 봉 제외')
        result = analyze(payload) if payload is not None else run_plan(args.symbol or '005930', args.market or 'KR')
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, RuntimeError, KeyError, TypeError, OSError):
        # 입력 전체나 예외 본문에 자격 증명이 섞여 있을 수 있어 일반 오류로 한정합니다.
        parser.exit(2, '분석 실패: 입력 형식·데이터 날짜·API 인증을 확인하세요.\n')


if __name__ == '__main__':
    main()
