#!/usr/bin/env bash
# ==============================================================================
# 파일명: deploy_api_gateway.sh
# 목적: Google Cloud API Gateway에 사용자 정의 API 등록 및 배포 자동화
# 환경: Linux / Bash / Google Cloud SDK (gcloud CLI 필요)
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 환경 변수 및 설정 정의
# 주의: 실제 GCP 프로젝트 ID와 서비스 계정을 환경에 맞게 확인/수정하십시오.
# ------------------------------------------------------------------------------
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
REGION="asia-northeast1"
API_ID="sps-mcp-api"
API_DISPLAY_NAME="SPS MCP API"
CONFIG_ID="sps-mcp-cfg-v19"
CONFIG_DISPLAY_NAME="SPS MCP Master Config v19 Full"
GATEWAY_ID="sps-mcp-gateway"
OPENAPI_SPEC="./openapi-spec.yaml"

# 백엔드 인증 서비스 계정 (필요한 경우 지정, 기본 빈 문자열)
# 예: backend-auth-sa@${PROJECT_ID}.iam.gserviceaccount.com
BACKEND_AUTH_SA="${BACKEND_AUTH_SA:-}"

echo "=========================================================="
echo "SPS API Gateway 배포 프로세스를 시작합니다."
echo "프로젝트: ${PROJECT_ID:-'(미지정)'}"
echo "리전: ${REGION}"
echo "API ID: ${API_ID}"
echo "Config ID: ${CONFIG_ID}"
echo "Gateway ID: ${GATEWAY_ID}"
echo "=========================================================="

if [ -z "${PROJECT_ID}" ]; then
  echo "[오류] GCP 프로젝트 ID가 설정되지 않았습니다. gcloud config set project [PROJECT_ID]를 먼저 실행하십시오."
  exit 1
fi

if [ ! -f "${OPENAPI_SPEC}" ]; then
  echo "[오류] OpenAPI 사양 파일(${OPENAPI_SPEC})이 존재하지 않습니다."
  exit 1
fi

# ==============================================================================
# 1단계: 사용자 정의 API 리소스 생성 (최초 1회 등록)
# 목적: API Gateway의 논리적 최상위 API 컨테이너를 생성
# ==============================================================================
echo ""
echo "[1단계] 사용자 정의 API 리소스(${API_ID}) 확인 및 등록..."
if gcloud api-gateway apis describe "${API_ID}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "-> API 리소스(${API_ID})가 이미 등록되어 있어 생성을 건너뜁니다."
else
  echo "-> 신규 API 리소스(${API_ID}) 등록을 진행합니다."
  gcloud api-gateway apis create "${API_ID}" \
      --project="${PROJECT_ID}" \
      --display-name="${API_DISPLAY_NAME}"
  echo "-> API 리소스(${API_ID}) 생성 완료."
fi

# ==============================================================================
# 2단계: 신규 Config 생성 (sps-mcp-cfg-v19)
# 목적: openapi-spec.yaml을 파싱하여 게이트웨이 라우팅 구성 등록
# ==============================================================================
echo ""
echo "[2단계] 신규 API Config(${CONFIG_ID}) 생성..."
if gcloud api-gateway api-configs describe "${CONFIG_ID}" --api="${API_ID}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "-> API Config(${CONFIG_ID})가 이미 존재합니다. 신규 배포를 위해 고유한 Config ID를 권장합니다."
else
  CREATE_CONFIG_CMD=(
    gcloud api-gateway api-configs create "${CONFIG_ID}"
    --api="${API_ID}"
    --openapi-spec="${OPENAPI_SPEC}"
    --display-name="${CONFIG_DISPLAY_NAME}"
    --project="${PROJECT_ID}"
  )
  if [ -n "${BACKEND_AUTH_SA}" ]; then
    CREATE_CONFIG_CMD+=(--backend-auth-service-account="${BACKEND_AUTH_SA}")
  fi

  echo "-> 실행 명령: ${CREATE_CONFIG_CMD[*]}"
  "${CREATE_CONFIG_CMD[@]}"
  echo "-> API Config(${CONFIG_ID}) 생성 완료."
fi

# ==============================================================================
# 3단계: 게이트웨이 즉시 배포 (생성 또는 업데이트)
# 목적: 게이트웨이 인스턴스에 최신 Config를 바인딩하여 트래픽 반영
# ==============================================================================
echo ""
echo "[3단계] 게이트웨이(${GATEWAY_ID}) 배포/업데이트..."
if gcloud api-gateway gateways describe "${GATEWAY_ID}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "-> 기존 게이트웨이(${GATEWAY_ID})를 최신 Config(${CONFIG_ID})로 업데이트합니다."
  gcloud api-gateway gateways update "${GATEWAY_ID}" \
      --location="${REGION}" \
      --api="${API_ID}" \
      --api-config="${CONFIG_ID}" \
      --project="${PROJECT_ID}"
else
  echo "-> 게이트웨이(${GATEWAY_ID})가 존재하지 않아 신규 생성합니다."
  gcloud api-gateway gateways create "${GATEWAY_ID}" \
      --location="${REGION}" \
      --api="${API_ID}" \
      --api-config="${CONFIG_ID}" \
      --project="${PROJECT_ID}"
fi

# ==============================================================================
# 4단계: 배포 상태 및 게이트웨이 엔드포인트 URL 검증
# ==============================================================================
echo ""
echo "[4단계] 배포 상태 확인 및 호스트 URL 조회..."
GW_URL=$(gcloud api-gateway gateways describe "${GATEWAY_ID}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(defaultHostname)" 2>/dev/null || echo "미확인")

echo "=========================================================="
echo "배포 완료!"
echo "게이트웨이 호스트: https://${GW_URL}"
echo "테스트 예시:"
echo "  curl -k https://${GW_URL}/.well-known/openid-configuration"
echo "=========================================================="