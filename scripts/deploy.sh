#!/bin/bash
# =============================================================================
# scripts/deploy.sh ★ 7.12.0
# ⭐ 자동 배포 스크립트 — ZIP 위치만 지정하면 전부 자동!
#
# ─── 사용 방법 ───────────────────────────────────────────
#
# [STEP 1] Windows → Linux로 ZIP 파일 전송 (Windows PowerShell에서 실행)
#
#   scp -i $HOME\.ssh\google_compute_engine \
#       C:\Users\jeaje\Downloads\vm_project_v7.12.0.zip \
#       jeaje@34.64.209.152:~/
#
# ─────────────────────────────────────────────────────────
#
# [STEP 2] Linux VM에서 배포 실행
#
#   첫 설치 시:
#     cd ~
#     unzip vm_project_v7.12.0.zip        ← 압축 해제
#     cd vm_project                         ← 폴더 이동
#     bash scripts/deploy.sh ~/vm_project_v7.12.0.zip ~/vm_project
#
#   업데이트 시 (이미 설치된 경우):
#     bash ~/vm_project/scripts/deploy.sh ~/vm_project_v7.12.0.zip ~/vm_project
#
# ─────────────────────────────────────────────────────────
#
# [서버 관리 명령어 모음]
#
#   서버 상태 확인:
#     sudo lsof -i :8000
#     curl http://127.0.0.1:8000/api/status
#
#   서버 시작:
#     cd ~/vm_project && nohup python3 run_server.py > logs/flask.log 2>&1 &
#
#   서버 종료:
#     sudo kill -9 $(sudo lsof -t -i :8000)
#
#   서버 재시작:
#     sudo kill -9 $(sudo lsof -t -i :8000) && \
#     cd ~/vm_project && nohup python3 run_server.py > logs/flask.log 2>&1 &
#
#   로그 확인:
#     tail -f ~/vm_project/logs/flask.log
#
#   DB 시작:
#     sudo systemctl start mongod
#     sudo systemctl start mariadb
#
#   방화벽 포트 열기:
#     gcloud compute firewall-rules create allow-8000 --allow tcp:8000 --source-ranges 0.0.0.0/0
#
# [버전 이력]
#   7.12.0 (2026-06-16): scp 명령어 추가, 서버 명령어 모음 추가
#   7.10.1 (2026-06-16): 최초 생성
# =============================================================================

set -e

# ─── 색깔 출력 ───────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; PURPLE='\033[0;35m'; NC='\033[0m'

log_info()  { echo -e "${GREEN}[✅ INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[⚠️  WARN]${NC} $1"; }
log_error() { echo -e "${RED}[❌ ERROR]${NC} $1"; exit 1; }
log_step()  { echo -e "${BLUE}[🔄 STEP]${NC} $1"; }

# ─── 설정값 ──────────────────────────────────────────────
ZIP_FILE="${1:-}"
INSTALL_DIR="${2:-/home/$(whoami)/vm_project}"
BACKUP_BASE="/home/$(whoami)/vm_backups"
SERVER_PORT=8000
PYTHON="python3"

# ─── 배너 ────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║   🧠 VM Project 자동 배포 스크립트 v7.12.0          ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── STEP 0: 입력값 확인 ─────────────────────────────────
log_step "STEP 0: 입력값 확인"

if [ -z "$ZIP_FILE" ]; then
    echo -e "${YELLOW}ZIP 파일 경로를 입력하세요 (예: ~/vm_project_v7.12.0.zip):${NC}"
    read -r ZIP_FILE
fi

[ ! -f "$ZIP_FILE" ] && log_error "ZIP 파일 없음: $ZIP_FILE"

VERSION=$(basename "$ZIP_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="vm_project_backup_v${VERSION}_${TIMESTAMP}"

echo ""
echo -e "  📦 ZIP 파일:  ${BLUE}$ZIP_FILE${NC}"
echo -e "  📁 설치위치:  ${BLUE}$INSTALL_DIR${NC}"
echo -e "  💾 백업위치:  ${BLUE}${BACKUP_BASE}/${BACKUP_NAME}.tar.gz${NC}"
echo -e "  🔢 버전:      ${BLUE}v$VERSION${NC}"
echo ""
echo -e "${YELLOW}⚠️  기존 프로젝트를 백업 후 초기화합니다. 계속할까요? (y/N)${NC}"
read -r CONFIRM
[[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]] && { log_warn "배포 취소됨"; exit 0; }

# ─── STEP 1: 기존 서버 종료 ──────────────────────────────
log_step "STEP 1: 기존 서버 종료"

PID=$(sudo lsof -t -i :$SERVER_PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
    sudo kill -9 $PID 2>/dev/null || true
    sleep 1
    log_info "서버 종료됨 (PID: $PID)"
else
    log_info "실행 중인 서버 없음"
fi

# ─── STEP 2: 기존 프로젝트 백업 ──────────────────────────
log_step "STEP 2: 기존 프로젝트 백업"

mkdir -p "$BACKUP_BASE"

if [ -d "$INSTALL_DIR" ]; then
    BACKUP_PATH="${BACKUP_BASE}/${BACKUP_NAME}.tar.gz"
    tar -czf "$BACKUP_PATH" \
        --exclude="*/logs/*" \
        --exclude="*/__pycache__/*" \
        --exclude="*/models/*.pkl" \
        -C "$(dirname "$INSTALL_DIR")" \
        "$(basename "$INSTALL_DIR")" 2>/dev/null || true
    log_info "백업 완료: $BACKUP_PATH ($(du -sh $BACKUP_PATH | cut -f1))"
    # 오래된 백업 정리 (최근 5개 유지)
    ls -t "$BACKUP_BASE"/*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
else
    log_warn "기존 프로젝트 없음 — 첫 설치"
fi

# ─── STEP 3: 기존 파일 삭제 ──────────────────────────────
log_step "STEP 3: 기존 파일 삭제"

[ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR" && log_info "삭제 완료"

# ─── STEP 4: ZIP 압축 해제 → vm_project 폴더로 설치 ─────
log_step "STEP 4: 새 버전 설치 (v$VERSION)"

PARENT_DIR=$(dirname "$INSTALL_DIR")
INSTALL_NAME=$(basename "$INSTALL_DIR")
mkdir -p "$PARENT_DIR"
cd "$PARENT_DIR"

# 압축 해제
unzip -q "$ZIP_FILE"

# 압축 해제된 폴더 이름 확인 후 vm_project 로 rename
EXTRACTED=$(unzip -Z1 "$ZIP_FILE" | head -1 | cut -d'/' -f1)
if [ "$EXTRACTED" != "$INSTALL_NAME" ] && [ -d "$EXTRACTED" ]; then
    mv "$EXTRACTED" "$INSTALL_NAME"
    log_info "폴더 rename: $EXTRACTED → $INSTALL_NAME"
fi

log_info "설치 완료: $INSTALL_DIR"

# ─── STEP 5: 필수 폴더 + 실행권한 ───────────────────────
log_step "STEP 5: 폴더 생성 및 권한 설정"

cd "$INSTALL_DIR"
mkdir -p logs outputs/charts outputs/reports models data uploads data_lake
chmod +x scripts/*.sh 2>/dev/null || true
log_info "완료"

# ─── STEP 6: 패키지 설치 ─────────────────────────────────
log_step "STEP 6: Python 패키지 설치"

$PYTHON -m pip install -r requirements.txt --break-system-packages -q 2>&1 | tail -2
log_info "완료"

# ─── STEP 7: DB 시작 ─────────────────────────────────────
log_step "STEP 7: DB 서비스 시작"

sudo systemctl start mongod  2>/dev/null && log_info "MongoDB 시작됨" || log_warn "MongoDB 실패"
sudo systemctl start mariadb 2>/dev/null && log_info "MariaDB 시작됨" || log_warn "MariaDB 실패"

# ─── STEP 8: Cron 등록 ───────────────────────────────────
log_step "STEP 8: Cron 자동 등록"

$PYTHON -c "
import sys; sys.path.insert(0,'.')
from scheduler.cron_jobs import register_crontab
register_crontab()
" 2>/dev/null && log_info "완료" || log_warn "Cron 등록 실패 (수동 등록 필요)"

# ─── STEP 9: Flask 서버 시작 ─────────────────────────────
log_step "STEP 9: Flask 서버 시작"

nohup $PYTHON run_server.py > logs/flask.log 2>&1 &
sleep 3

curl -s http://127.0.0.1:$SERVER_PORT/api/status > /dev/null 2>&1 \
    && log_info "서버 정상 시작됨" \
    || log_warn "서버 확인 실패 → tail -f logs/flask.log 확인"

# ─── 완료 요약 ────────────────────────────────────────────
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "VM_IP")
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║   🎉 배포 완료!                                      ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  🔢 버전:      ${GREEN}v$VERSION${NC}"
echo -e "  📁 위치:      ${GREEN}$INSTALL_DIR${NC}"
echo -e "  💾 백업:      ${GREEN}$BACKUP_PATH${NC}"
echo -e "  🌐 대시보드:  ${GREEN}http://${SERVER_IP}:$SERVER_PORT${NC}"
echo -e "  📡 API:       ${GREEN}http://127.0.0.1:$SERVER_PORT/api/status${NC}"
echo ""
echo -e "  ──── 자주 쓰는 명령어 ────────────────────────────────"
echo -e "  로그:   ${BLUE}tail -f $INSTALL_DIR/logs/flask.log${NC}"
echo -e "  재시작: ${BLUE}bash $INSTALL_DIR/scripts/deploy.sh [새ZIP] $INSTALL_DIR${NC}"
echo -e "  종료:   ${BLUE}sudo kill -9 \$(sudo lsof -t -i :$SERVER_PORT)${NC}"
echo ""
