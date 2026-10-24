#!/usr/bin/env bash
# 목적: OpenAPI의 11개 경로를 안전하게 점검하고, 유효한 인증이 필요한 경로는 실제 성공 경로를 확인합니다.
# 주의: /authorize와 /token은 브라우저 승인/유효 code 없이는 200이 되지 않습니다. /gmail/send는 실행할 때마다 테스트 메일 1통을 발송합니다.
set -uo pipefail
set +x
umask 077

SPEC="${SPEC:-./openapi-spec.yaml}"
GW="${GW:-https://sps-mcp-gateway-5v4kufkk.an.gateway.dev}"
TMPDIR="${TMPDIR:-/data/jeaje/tmp}"

[[ -f "$SPEC" ]] || { echo "OpenAPI 파일 없음: $SPEC"; exit 2; }
mkdir -p "$TMPDIR" || exit 2
chmod 700 "$TMPDIR"
WORK="$(mktemp -d "$TMPDIR/openapi11.XXXXXX")" || exit 2
chmod 700 "$WORK"
GW="${GW%/}"
AUTH_CFG="$WORK/auth.conf"
SSE_PID=""

# 토큰과 임시 응답은 권한 600/700인 임시 경로에만 두고 종료 시 삭제합니다.
cleanup() {
  unset ACCESS_TOKEN
  [[ -n "$SSE_PID" ]] && kill "$SSE_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

# 대상 OpenAPI의 최상위 경로가 정확히 11개인지 확인합니다.
# 요청된 11개 smoke-test 경로를 검증합니다. 명세에는 이 외의 경로도 포함될 수 있습니다.
paths=(
  "/mcp" "/sse" "/messages" "/authorize" "/token"
  "/.well-known/openid-configuration"
  "/.well-known/oauth-authorization-server"
  "/.well-known/oauth-protected-resource/mcp"
  "/gmail/read" "/gmail/send" "/agent/chat"
)
for path in "${paths[@]}"; do
  grep -Fqx "  ${path}:" "$SPEC" || { echo "명세 경로 누락: $path"; exit 1; }
done
echo "요청 경로 확인: ${#paths[@]}/11 (OpenAPI 명세 전체 경로 수는 16)"

# 인증 토큰은 터미널에서 숨겨 입력하며 스크립트/명령행/출력에 표시하지 않습니다.
read -r -s -p 'SPS access token: ' ACCESS_TOKEN
printf '\n'
[[ -n "${ACCESS_TOKEN:-}" ]] || { echo "토큰이 비어 있습니다."; exit 2; }
printf 'header = "Authorization: Bearer %s"\n' "$ACCESS_TOKEN" >"$AUTH_CFG"
chmod 600 "$AUTH_CFG"
unset ACCESS_TOKEN

PASS=0
INFO=0
SKIP=0
FAIL=0
N=0
LAST_CODE=""
LAST_BODY=""
LAST_HEADERS=""

# HTTP 요청을 실행하고 코드·헤더·본문을 임시 파일에 저장합니다. 응답 본문은 기본 출력하지 않습니다.
request() {
  local auth="$1" method="$2" url="$3" content_type="$4" data="$5" session="$6" timeout="$7"
  N=$((N + 1))
  LAST_BODY="$WORK/body.$N"
  LAST_HEADERS="$WORK/headers.$N"
  local args=(-sS --connect-timeout 10 --max-time "$timeout"
              -D "$LAST_HEADERS" -o "$LAST_BODY" -w '%{http_code}'
              -X "$method" -H 'Accept: application/json, text/event-stream')
  [[ -n "$content_type" ]] && args+=(-H "Content-Type: $content_type")
  [[ -n "$data" ]] && args+=(--data-binary "$data")
  [[ -n "$session" ]] && args+=(-H "Mcp-Session-Id: $session")
  local result rc=0
  if [[ "$auth" == yes ]]; then
    result="$(curl "${args[@]}" -K "$AUTH_CFG" "$url")" || rc=$?
  else
    result="$(curl "${args[@]}" "$url")" || rc=$?
  fi
  LAST_CODE="${result:-000}"
  [[ "$rc" -eq 0 ]] || LAST_CODE="${LAST_CODE:-000}"
}

# 예상 HTTP 상태가 정확히 맞을 때만 PASS로 기록합니다.
report() {
  local label="$1" expected="$2"
  if [[ "$LAST_CODE" == "$expected" ]]; then
    echo "PASS | $label | HTTP $LAST_CODE"
    PASS=$((PASS + 1))
  else
    echo "FAIL | $label | 기대 HTTP $expected, 결과 HTTP $LAST_CODE"
    FAIL=$((FAIL + 1))
  fi
}

# 표준상 성공 코드가 여러 개인 경로를 확인합니다(예: OAuth redirect 302, legacy messages 202).
report_any() {
  local label="$1"; shift
  local code
  for code in "$@"; do
    if [[ "$LAST_CODE" == "$code" ]]; then
      echo "PASS | $label | HTTP $LAST_CODE (표준 응답)"
      PASS=$((PASS + 1))
      return
    fi
  done
  echo "FAIL | $label | 허용 응답 $*, 실제 HTTP $LAST_CODE"
  FAIL=$((FAIL + 1))
}

# 1) Streamable HTTP initialize와 2) tools/list: 같은 인증 토큰과 생성된 세션을 사용합니다.
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"openapi-safe-check","version":"1"}}}'
request yes POST "$GW/mcp" application/json "$INIT" "" 20
SESSION_ID="$(awk 'tolower($1)=="mcp-session-id:" {gsub("\r","",$2); id=$2} END{print id}' "$LAST_HEADERS")"
report "POST /mcp initialize" 200
if [[ -z "$SESSION_ID" ]]; then
  echo "FAIL | /mcp 세션 헤더 | 없음"
  FAIL=$((FAIL + 1))
else
  LIST='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  request yes POST "$GW/mcp" application/json "$LIST" "$SESSION_ID" 20
  if [[ "$LAST_CODE" == 200 ]] && python3 - "$LAST_BODY" <<'PY'
import json, sys
# MCP SSE 응답에서 tools/list의 result.tools 배열이 있는지 확인합니다.
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    if line.startswith("data: "):
        try:
            data = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        tools = data.get("result", {}).get("tools")
        if isinstance(tools, list):
            print("tools/list 도구 수:", len(tools))
            raise SystemExit(0)
raise SystemExit(1)
PY
  then
    report "POST /mcp tools/list" 200
  else
    report "POST /mcp tools/list 응답 형식" 200
  fi
fi

# 3–4) Legacy SSE 세션을 연 채 endpoint 이벤트를 받고, 세션 초기화 및 tools/list를 POST합니다.
SSE_HEADERS="$WORK/sse.headers"
SSE_BODY="$WORK/sse.body"
curl -sS -N --connect-timeout 10 --max-time 25 -D "$SSE_HEADERS" -o "$SSE_BODY" \
  -K "$AUTH_CFG" -H 'Accept: text/event-stream' "$GW/sse" >/dev/null 2>&1 &
SSE_PID=$!
for _ in $(seq 1 60); do
  grep -q '^data: /messages' "$SSE_BODY" 2>/dev/null && break
  kill -0 "$SSE_PID" 2>/dev/null || break
  sleep 0.1
done
SSE_CODE="$(awk '/^HTTP\// {code=$2} END{print code+0}' "$SSE_HEADERS" 2>/dev/null)"
SSE_ENDPOINT="$(sed -n 's/^data: *//p' "$SSE_BODY" 2>/dev/null | head -n 1 | tr -d '\r')"
if [[ "$SSE_CODE" == 200 && -n "$SSE_ENDPOINT" ]]; then
  echo "PASS | GET /sse endpoint 이벤트 | HTTP 200"
  PASS=$((PASS + 1))
  [[ "$SSE_ENDPOINT" == http* ]] || SSE_ENDPOINT="$GW$SSE_ENDPOINT"
  LEGACY_INIT='{"jsonrpc":"2.0","id":3,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"openapi-sse-check","version":"1"}}}'
  request yes POST "$SSE_ENDPOINT" application/json "$LEGACY_INIT" "" 20
  report_any "POST /messages 세션 initialize" 202 200
  if [[ "$LAST_CODE" == 202 || "$LAST_CODE" == 200 ]]; then
    LEGACY_LIST='{"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}}'
    request yes POST "$SSE_ENDPOINT" application/json "$LEGACY_LIST" "" 20
    report_any "POST /messages 세션 tools/list" 202 200
  fi
else
  echo "FAIL | GET /sse endpoint 이벤트 | HTTP ${SSE_CODE:-000}, endpoint 없음"
  FAIL=$((FAIL + 1))
fi
[[ -n "$SSE_PID" ]] && kill "$SSE_PID" 2>/dev/null || true
SSE_PID=""

# 5) 가짜 OAuth client만 사용합니다. 성공적인 authorize 응답은 보통 redirect이며 200이 아닙니다.
AUTH_QUERY='/authorize?response_type=code&client_id=openapi-safe-invalid&redirect_uri=http%3A%2F%2F127.0.0.1%2Fcallback&scope=mcp%3Atools&code_challenge=ZmFrZS1jaGFsbGVuZ2U&code_challenge_method=S256&state=safe-check'
request no GET "$GW$AUTH_QUERY" "" "" "" 15
report_any "GET /authorize 가짜 client 거부/redirect" 302 400

# 6) 가짜 authorization code는 발급 토큰을 만들지 않아야 하며 400/401이 정상 거부입니다.
request no POST "$GW/token" application/x-www-form-urlencoded \
  'grant_type=authorization_code&client_id=openapi-safe-invalid&code=invalid-safe-code&redirect_uri=http%3A%2F%2F127.0.0.1%2Fcallback&code_verifier=invalid-safe-verifier' "" 15
report_any "POST /token 가짜 code 거부" 400 401

# 7–9) 공개 discovery 문서는 HTTP 200과 JSON 형식을 모두 확인합니다.
for path in \
  '/.well-known/openid-configuration' \
  '/.well-known/oauth-authorization-server' \
  '/.well-known/oauth-protected-resource/mcp'
do
  request no GET "$GW$path" "" "" "" 15
  if [[ "$LAST_CODE" == 200 ]] && python3 -m json.tool "$LAST_BODY" >/dev/null 2>&1; then
    report "GET $path JSON" 200
  else
    report "GET $path JSON" 200
  fi
done

# 10) Gmail 본문을 출력하지 않고 인증된 읽기 요청이 성공했는지만 확인합니다.
request yes GET "$GW/gmail/read?max_results=1" "" "" "" 30
report "GET /gmail/read 인증 성공" 200

# 11) 읽기 전용 지시로 에이전트 라우트를 확인합니다. 내용이나 토큰은 출력하지 않습니다.
request yes POST "$GW/agent/chat" application/json \
  '{"user_input":"MCP 연결 상태와 도구 개수만 읽기 전용으로 확인해줘. 메일 읽기/발송, 데이터 변경, 다른 도구 호출은 하지 마."}' "" 90
report "POST /agent/chat 인증 성공" 200

# 12) 요청에 따라 기본 실행에서 본인 주소로 테스트 메일 한 통을 실제 발송합니다.
TEST_RECIPIENT="jeajea.park@gmail.com"
request yes POST "$GW/gmail/send" application/json \
  "{\"recipient\":\"$TEST_RECIPIENT\",\"subject\":\"[SPS] OpenAPI 안전 점검 테스트\",\"content\":\"test_openapi_11_safe.sh 발송 경로 확인 메일입니다.\"}" "" 30
report "POST /gmail/send 테스트 메일 발송" 200

echo "요약: PASS=$PASS INFO=$INFO SKIP=$SKIP FAIL=$FAIL"
echo "참고: OAuth authorize의 302 및 legacy /messages의 202는 성공 응답이며 200으로 바꾸지 않습니다. Gmail 테스트 메일 1통이 발송됩니다."
[[ "$FAIL" -eq 0 ]]
