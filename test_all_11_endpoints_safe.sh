#!/usr/bin/env bash
# SPS Gateway 안전 진단: MCP와 공개 메타데이터만 실제 호출하고,
# 이메일 발송·메일 열람·에이전트 작업 등 부작용 가능 요청은 실행하지 않습니다.
set -Eeuo pipefail
umask 077

GW="${GW:-https://sps-mcp-gateway-5v4kufkk.an.gateway.dev}"
TIMEOUT="${TIMEOUT:-20}"
TMP_DIR="$(mktemp -d)"
trap 'unset ACCESS_TOKEN MCP_SESSION_ID; rm -rf "$TMP_DIR"' EXIT

ok=0
warn=0
skip=0
fail=0

report() {
  local n="$1" result="$2" detail="$3"
  printf '%02d | %-8s | %s\n' "$n" "$result" "$detail"
  case "$result" in PASS) ((ok+=1));; WARN) ((warn+=1));; SKIP) ((skip+=1));; FAIL) ((fail+=1));; esac
}

http_get() {
  local name="$1" path="$2"
  curl -sS --max-time "$TIMEOUT" -o "$TMP_DIR/$name.body" \
    -w '%{http_code}' "$GW$path" 2>"$TMP_DIR/$name.err" || true
}

printf 'SPS Gateway: %s\n' "$GW"
printf '진단 시작 (비밀값은 출력하지 않습니다)\n\n'

# MCP Streamable HTTP는 인증된 initialize 뒤 같은 세션으로 tools/list를 호출합니다.
# 대화형 입력은 숨기고, 자동화할 때는 stdin으로 받아 인자·로그 노출을 피합니다.
if [[ -t 0 ]]; then
  read -rsp '유효한 access token 입력: ' ACCESS_TOKEN
  printf '\n'
else
  IFS= read -r ACCESS_TOKEN
fi
if [[ -z "$ACCESS_TOKEN" ]]; then
  report 1 FAIL 'MCP 토큰이 비어 있음'
else
  # curl 설정 파일 권한을 제한하고 종료 시 삭제해 토큰을 명령행·출력에 남기지 않습니다.
  printf 'header = "Authorization: Bearer %s"\n' "$ACCESS_TOKEN" > "$TMP_DIR/auth.curl"
  chmod 600 "$TMP_DIR/auth.curl"
  init_status="$(curl -sS --max-time "$TIMEOUT" --config "$TMP_DIR/auth.curl" \
    -D "$TMP_DIR/init.headers" -o "$TMP_DIR/init.body" -w '%{http_code}' \
    "$GW/mcp" -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"safe-diagnostic","version":"1"}}}' 2>"$TMP_DIR/init.err" || true)"
  MCP_SESSION_ID="$(awk 'tolower($1)=="mcp-session-id:" {gsub("\r", "", $2); id=$2} END {print id}' "$TMP_DIR/init.headers" 2>/dev/null || true)"
  if [[ "$init_status" != 200 || -z "$MCP_SESSION_ID" ]]; then
    report 1 FAIL "initialize HTTP $init_status (토큰 또는 세션 확인 필요)"
  else
    list_status="$(curl -sS --max-time "$TIMEOUT" --config "$TMP_DIR/auth.curl" \
      -D "$TMP_DIR/list.headers" -o "$TMP_DIR/list.body" -w '%{http_code}' \
      "$GW/mcp" -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -H "Mcp-Session-Id: $MCP_SESSION_ID" \
      -H 'MCP-Protocol-Version: 2025-06-18' \
      --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' 2>"$TMP_DIR/list.err" || true)"
    tool_count="$(python3 - "$TMP_DIR/list.body" <<'PY'
import json, sys
try:
    line = next(x[6:] for x in open(sys.argv[1], encoding='utf-8') if x.startswith('data: '))
    result = json.loads(line).get('result', {})
    print(len(result.get('tools', [])) if isinstance(result.get('tools'), list) else -1)
except Exception:
    print(-1)
PY
)"
    if [[ "$list_status" == 200 && "$tool_count" =~ ^[0-9]+$ && "$tool_count" -ge 0 ]]; then
      report 1 PASS "initialize + tools/list HTTP 200, tools=$tool_count"
    else
      report 1 FAIL "tools/list HTTP $list_status, 응답 파싱=$tool_count"
    fi
  fi
fi

# 구형 SSE·messages 경로는 현재 Streamable HTTP 사용 여부를 확인할 때까지 요청하지 않습니다.
report 2 SKIP 'GET /sse: 구형 SSE 경로; 현재 MCP는 /mcp Streamable HTTP로 검증'
report 3 SKIP 'POST /messages: 구형 메시지 경로; /mcp 세션 프로토콜 사용'

# OAuth 흐름은 실제 브라우저 승인과 PKCE verifier가 있어야 하므로 코드 교환을 흉내내지 않습니다.
report 4 SKIP 'GET /authorize: 실제 client_id·등록 redirect_uri·PKCE·브라우저 승인 필요'
report 5 SKIP 'POST /token: 유효한 authorization code와 code_verifier 없이는 실행하지 않음'

# 공개 메타데이터만 조회합니다. 본문 전체를 출력하지 않습니다.
for spec in \
  '6|/.well-known/openid-configuration' \
  '7|/.well-known/oauth-authorization-server' \
  '8|/.well-known/oauth-protected-resource/mcp'; do
  n="${spec%%|*}"; path="${spec#*|}"; name="meta$n"
  status="$(http_get "$name" "$path")"
  if [[ "$status" == 200 ]]; then report "$n" PASS "$path HTTP 200 JSON"; else report "$n" FAIL "$path HTTP $status"; fi
done

# 두 OAuth discovery 문서의 인증 방식 차이를 비교하되 비밀값은 읽거나 출력하지 않습니다.
python3 - "$TMP_DIR/meta6.body" "$TMP_DIR/meta7.body" <<'PY'
import json, sys
try:
    a, b = (json.load(open(p, encoding='utf-8')) for p in sys.argv[1:])
    x = a.get('token_endpoint_auth_methods_supported')
    y = b.get('token_endpoint_auth_methods_supported')
    if x != y:
        print(f'주의: OAuth 메타데이터 token auth methods 불일치: OpenID={x!r}; Authorization Server={y!r}')
    else:
        print(f'OAuth 메타데이터 token auth methods 일치: {x!r}')
except Exception:
    print('OAuth 메타데이터 비교 미확인: 응답 JSON 파싱 실패')
PY

# 개인 메일 열람과 외부 메일 발송, 에이전트 실행은 자동 테스트에서 제외합니다.
report 9 SKIP 'GET /gmail/read: 메일 내용 접근이므로 자동 호출하지 않음'
report 10 SKIP 'POST /gmail/send: 외부 메일 발송이므로 실행하지 않음'
report 11 SKIP 'POST /agent/chat: 에이전트가 도구·업무 작업을 실행할 수 있어 자동 호출하지 않음'

printf '\n요약: PASS=%d WARN=%d SKIP=%d FAIL=%d\n' "$ok" "$warn" "$skip" "$fail"
printf '주의: OAuth client secret을 스크립트에 저장하지 말고, 노출된 시크릿은 폐기·교체하세요.\n'

# chmod +x test_all_11_endpoints_safe.sh
# ./test_all_11_endpoints_safe.sh