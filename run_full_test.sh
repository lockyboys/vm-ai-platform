#!/bin/bash

GW="https://sps-mcp-gateway-5v4kufkk.an.gateway.dev"
CLIENT_ID="00914338-4226-46c0-80dc-5ac1b00f13d5"
CLIENT_SECRET="36ad13904852b83c31fa470edde628da861c014fd77ba3e792238c03a0b37807"

echo "=========================================================="
echo "      🚀 SPS MCP Master Gateway 전수 테스트               "
echo "=========================================================="

# 1. ChatGPT 연동 핵심 Discovery 검사
echo -n "1. OAuth Authorization Server Discovery: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$GW/.well-known/oauth-authorization-server"

echo -n "2. OpenID Configuration Discovery: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$GW/.well-known/openid-configuration"

echo -n "3. OAuth Protected Resource Metadata: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$GW/.well-known/oauth-protected-resource/mcp"

# 2. OAuth 인증 흐름 검사
echo -n "4. Authorize Endpoint (리디렉션 확인): "
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$GW/authorize?response_type=code&client_id=$CLIENT_ID"

echo -n "5. Token Endpoint (파라미터 검증 확인): "
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$GW/token" -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=authorization_code"

# 3. MCP Core 통신 검사
echo -n "6. MCP Status (GET): "
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$GW/mcp"

echo -n "7. MCP RPC (POST, 인증 미들웨어 도달 확인): "
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$GW/mcp" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# 4. 부가 서비스 라우팅 검사
echo -n "8. Gmail Read 라우팅: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$GW/gmail/read"

echo -n "9. Gmail Send 라우팅: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$GW/gmail/send" -H "Content-Type: application/json" -d '{"to":"test@test.com"}'

echo -n "10. Agent Chat 라우팅: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$GW/agent/chat" -H "Content-Type: application/json" -d '{"message":"hi"}'

echo "=========================================================="
echo "테스트 완료!"
