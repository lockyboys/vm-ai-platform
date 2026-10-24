#!/usr/bin/env bash
# 목적: OpenAPI에 선언된 11개 경로를 점검합니다.
# 주의: Gmail 발송·메일 읽기·에이전트 실행은 인증 없는 요청만 보내 부작용을 막습니다.
set -uo pipefail
set +x

SPEC="${SPEC:-./openapi-spec.yaml}"
GW="${GW:-https://sps-mcp-gateway-5v4kufkk.an.gateway.dev}"
TMPDIR="${TMPDIR:-/data/jeaje/tmp}"

[[ -f "$SPEC" ]] || { echo "명세 파일 없음: $SPEC"; exit 1; }
mkdir -p "$TMPDIR" || exit 1
chmod 700 "$TMPDIR"
WORK="$(mktemp -d "$TMPDIR/openapi11.XXXXXX")" || exit 1
chmod 700 "$WORK"
trap 'unset ACCESS_TOKEN; rm -rf "$WORK"' EXIT

# 명세에 대상 11개 경로가 모두 있는지 먼저 확인합니다.
paths=(
  "/mcp:" "/sse:" "/messages:" "/authorize:" "/token:"
  "/.well-known/openid-configuration:"
  "/.well-known/oauth-authorization-server:"
  "/.well-known/oauth-protected-resource/mcp:"
  "/gmail/read:" "/gmail/send:" "/agent/chat:"
)
for p in "${paths[@]}"; do
  grep -Fq "  $p" "$SPEC" || { echo "명세 경로 누락: $p"; exit 1; }
done
echo "OpenAPI 경로 확인: 11/11"

read -r -s -p 'MCP access token 입력: ' ACCESS_TOKEN
printf '\n'
[[ -n "$ACCESS_TOKEN" ]] || { echo "토큰이 비어 있습니다."; exit 1; }

PASS=0
INFO=0
FAIL=0
N=0
LAST_CODE=""
LAST_BODY=""
LAST_HEADERS=""

request() {
  # 인자: 인증사용여부 메서드 경로 콘텐츠유형 본문 세션ID 제한시간
  local auth="$1" method="$2" path="$3" content_type="$4"
  local data="$5" session_id="$6" timeout="$7"
  N=$((N + 1))
  LAST_BODY="$WORK/body.$N"
  LAST_HEADERS="$WORK/headers.$N"
  local args=(-sS --max-time "$timeout" -X "$method"
              -D "$LAST_HEADERS" -o "$LAST_BODY" -w '%{http_code}'
              -H "Accept: application/json, text/event-stream")
  [[ -n "$content_type" ]] && args+=(-H "Content-Type: $content_type")
  [[ -n "$data" ]] && args+=(--data-binary "$data")
  [[ -n "$session_id" ]] && args+=(-H "Mcp-Session-Id: $session_id")

  local result rc=0
  if [[ "$auth" == yes ]]; then
    result="$(printf 'header = "Authorization: Bearer %s"\n' "$ACCESS_TOKEN" |
      curl "${args[@]}" -K - "$GW$path")" || rc=$?
  else
    result="$(curl "${args[@]}" "$GW$path")" || rc=$?
  fi
  LAST_CODE="${result:-000}"
  # 타임아웃 등 curl 오류는 응답 코드와 함께 진단 정보로 남깁니다.
  [[ "$rc" -eq 0 ]] || LAST_CODE="${LAST_CODE:-000}"
}

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

# 1. Streamable HTTP 초기화와 세션 생성
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"openapi-smoke","version":"1"}}}'
request yes POST /mcp application/json "$INIT" "" 20
SESSION_ID="$(awk 'tolower($1)=="mcp-session-id:" {gsub("\r","",$2); id=$2} END{print id}' "$LAST_HEADERS")"
report "POST /mcp initialize" 200
if [[ -z "$SESSION_ID" ]]; then
  echo "FAIL | MCP 세션 헤더 없음"
  FAIL=$((FAIL + 1))
fi

# 2. 도구 목록 조회: 생성한 세션을 재사용합니다.
request yes POST /mcp application/json \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  "$SESSION_ID" 20
if [[ "$LAST_CODE" == 200 ]] && python3 - "$LAST_BODY" <<'PY'
import json, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
for line in text.splitlines():
    if line.startswith("data: "):
        try:
            result = json.loads(line[6:]).get("result", {})
            tools = result.get("tools", [])
            print("tools/list 도구 수:", len(tools))
            raise SystemExit(0 if isinstance(tools, list) else 1)
        except json.JSONDecodeError:
            pass
raise SystemExit(1)
PY
then
  report "POST /mcp tools/list" 200
else
  report "POST /mcp tools/list" 200
fi

# 3–5. 레거시 SSE/메시지 및 OAuth 흐름은 안전한 무로그인 probe만 수행합니다.
request no GET /sse "" "" "" 4
echo "INFO | GET /sse 레거시 경로 probe | HTTP $LAST_CODE"
INFO=$((INFO + 1))

request no POST /messages application/json '{}' "" 10
echo "INFO | POST /messages 세션 없는 probe | HTTP $LAST_CODE"
INFO=$((INFO + 1))

AUTH_QUERY='/authorize?response_type=code&client_id=openapi-smoke-invalid&redirect_uri=http%3A%2F%2F127.0.0.1%2Fcallback&scope=mcp%3Atools&code_challenge=ZmFrZS1zbW9rZS1jaGFsbGVuZ2U&code_challenge_method=S256&state=smoke'
request no GET "$AUTH_QUERY" "" "" "" 10
echo "INFO | GET /authorize 가짜 client probe(로그인/승인 안 함) | HTTP $LAST_CODE"
INFO=$((INFO + 1))

request no POST /token application/x-www-form-urlencoded \
  'grant_type=authorization_code&client_id=openapi-smoke-invalid&code=invalid-smoke-code&redirect_uri=http%3A%2F%2F127.0.0.1%2Fcallback&code_verifier=invalid-smoke-verifier' \
  "" 10
echo "INFO | POST /token 가짜 code probe(토큰 교환 안 됨) | HTTP $LAST_CODE"
INFO=$((INFO + 1))

# 6–8. 공개 OAuth 메타데이터는 HTTP 200과 JSON 형식을 검사합니다.
for path in \
  '/.well-known/openid-configuration' \
  '/.well-known/oauth-authorization-server' \
  '/.well-known/oauth-protected-resource/mcp'
do
  request no GET "$path" "" "" "" 15
  if [[ "$LAST_CODE" == 200 ]] &&
     python3 -m json.tool "$LAST_BODY" >/dev/null 2>&1; then
    report "GET $path JSON" 200
  else
    report "GET $path JSON" 200
  fi
done

# 9–11. 실제 메일·에이전트 동작 없이 무토큰 요청이 차단되는지만 확인합니다.
request no GET '/gmail/read?max_results=1' "" "" "" 15
report "GET /gmail/read 무토큰 차단" 401

request no POST /gmail/send application/json \
  '{"recipient":"invalid-smoke","subject":"auth probe","content":"must not send"}' \
  "" 15
report "POST /gmail/send 무토큰 차단(메일 발송 없음)" 401

request no POST /agent/chat application/json \
  '{"user_input":"auth probe; do not execute"}' "" 15
report "POST /agent/chat 무토큰 차단(에이전트 실행 없음)" 401

echo "요약: PASS=$PASS INFO=$INFO FAIL=$FAIL"
[[ "$FAIL" -eq 0 ]]

# chmod +x ./test_openapi_11.sh
# TMPDIR=/data/jeaje/tmp ./test_openapi_11.sh