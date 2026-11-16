# use-ulixee-hero-crawler

Ulixee Hero 기반의 동적 웹페이지 분석 및 수집 어댑터 생성 스킬입니다.

## 강화된 기능

- 공개 페이지 passive probe
- 사용자 소유 브라우저 프로필·쿠키·storage state 재사용
- visible/headful 로그인 세션
- 로그인·MFA·동의·CAPTCHA 화면에서 자동 일시정지
- 사용자가 정상 절차로 완료한 뒤 자동 검증·재개
- SPA·목록·상세·모달·드로어·지도 패널 탐지
- virtualized list·무한 스크롤·페이지네이션 처리
- 401·403·429·WAF·세션 만료 감지
- 체크포인트 저장과 재개
- 비밀정보·쿠키·인증 헤더 로그 마스킹
- TypeScript Ulixee Hero adapter 생성
- 소량 비파괴 검증

## 호출 예시

```text
$use-ulixee-hero-crawler passive probe https://example.com/page
```

```text
$use-ulixee-hero-crawler authenticated probe https://example.com/account
```

```text
$use-ulixee-hero-crawler 이 페이지에 내가 정상 로그인한 브라우저 세션을 사용해서
목록과 상세 패널 동작을 판별하고 수집 어댑터를 만들어줘.
로그인, MFA, 동의 또는 CAPTCHA가 나오면 내가 직접 처리할 때까지 멈췄다가
성공 조건을 확인한 후 이어서 진행해.
```

## 접근 방식

```text
대상 URL
    ↓
정상 공개 접근 또는 사용자 승인 세션 연결
    ↓
로그인·MFA·CAPTCHA 필요 시 수동 완료 대기
    ↓
인증 성공 조건 검증
    ↓
Passive Probe
    ↓
SSR / CSR / SPA 판별
    ↓
목록 / 상세 / 모달 / 드로어 / 지도 패널 판별
    ↓
안정적인 Selector 탐색
    ↓
Adapter 생성
    ↓
소량 검증
    ↓
JSON + 증거 + 체크포인트
```

로그인·CAPTCHA·접근통제를 기술적으로 우회하지 않습니다. 대신 정상 사용자 세션, 수동 challenge 완료, 공식 API·내보내기·allowlist 같은 승인된 접근 경로를 최대한 활용합니다.
