#!/bin/bash
# =============================================================================
# launcher.sh ★ 7.12.0
# ⭐ VM 런처 — 최초 1회 설치 후 이것만 쓰면 돼요!
#
# 초등학생 설명:
#   리모컨처럼 이 파일 하나로 모든 배포를 자동으로 해줘요!
#
# ─── 최초 1회 설치 ───────────────────────────────────────
#
#   [Windows PowerShell] ZIP 전송:
#   scp -i $HOME\.ssh\google_compute_engine `
#       C:\Users\jeaje\Downloads\vm_project_v7.12.0.zip `
#       jeaje@34.64.209.152:~/
#
#   [VM 터미널] 런처 설치 (딱 한 번만!):
#   unzip -p ~/vm_project_v7.12.0.zip vm_project/scripts/launcher.sh > ~/launcher.sh
#   chmod +x ~/launcher.sh
#
# ─── 이후 업데이트는 이것만! ─────────────────────────────
#
#   [Windows PowerShell] 새 ZIP 전송:
#   scp -i $HOME\.ssh\google_compute_engine `
#       C:\Users\jeaje\Downloads\vm_project_v7.12.0.zip `
#       jeaje@34.64.209.152:~/
#
#   [VM 터미널] 런처 실행:
#   ~/launcher.sh ~/vm_project_v7.12.0.zip
#
# ─── 서버 관리 명령어 ────────────────────────────────────
#
#   상태확인:  curl http://127.0.0.1:8000/api/status
#   로그확인:  tail -f ~/vm_project/logs/flask.log
#   서버종료:  sudo kill -9 $(sudo lsof -t -i :8000)
#   서버시작:  cd ~/vm_project && nohup python3 run_server.py > logs/flask.log 2>&1 &
#   DB시작:    sudo systemctl start mongod mariadb
#
# [버전 이력]
#   7.12.0 (2026-06-16): 최초 생성
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
INSTALL_DIR="/home/$(whoami)/vm_project"   # 항상 고정!
BACKUP_BASE="/home/$(whoami)/vm_backups"
SERVER_PORT=8000
PYTHON="python3"

# ─── 배너 ────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║   🧠 VM Project 런처 v7.12.0                        ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── ZIP 파일 확인 ───────────────────────────────────────
if [ -z "$ZIP_FILE" ]; then
    echo -e "${YELLOW}ZIP 파일 경로를 입력하세요 (예: ~/vm_project_v7.12.0.zip):${NC}"
    read -r ZIP_FILE
fi

# ~ 경로 확장
ZIP_FILE="${ZIP_FILE/#\~/$HOME}"
[ ! -f "$ZIP_FILE" ] && log_error "ZIP 파일 없음: $ZIP_FILE"

# 버전 추출 (파일명에서)
VERSION=$(basename "$ZIP_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PATH="${BACKUP_BASE}/vm_project_backup_v${VERSION}_${TIMESTAMP}.tar.gz"

echo -e "  📦 ZIP:    ${BLUE}$ZIP_FILE${NC}"
echo -e "  📁 설치:   ${BLUE}$INSTALL_DIR${NC}"
echo -e "  💾 백업:   ${BLUE}$BACKUP_PATH${NC}"
echo -e "  🔢 버전:   ${BLUE}v$VERSION${NC}"
echo ""
echo -e "${YELLOW}⚠️  기존 프로젝트 백업 후 새 버전으로 교체합니다. (y/N)${NC}"
read -r CONFIRM
[[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]] && { echo "취소됨"; exit 0; }
echo ""

# ─── STEP 1: 기존 서버 종료 ──────────────────────────────
log_step "STEP 1/8 서버 종료"
PID=$(sudo lsof -t -i :$SERVER_PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
    sudo kill -9 $PID 2>/dev/null || true
    sleep 1
    log_info "종료됨 (PID: $PID)"
else
    log_info "실행 중인 서버 없음"
fi

# ─── STEP 2: 기존 프로젝트 백업 ──────────────────────────
log_step "STEP 2/8 기존 프로젝트 백업"
mkdir -p "$BACKUP_BASE"
if [ -d "$INSTALL_DIR" ]; then
    tar -czf "$BACKUP_PATH" \
        --exclude="*/logs/*" \
        --exclude="*/__pycache__/*" \
        --exclude="*/models/*.pkl" \
        -C "$(dirname "$INSTALL_DIR")" \
        "$(basename "$INSTALL_DIR")" 2>/dev/null || true
    log_info "백업 완료: $BACKUP_PATH ($(du -sh $BACKUP_PATH 2>/dev/null | cut -f1))"
    # 최근 5개만 유지
    ls -t "$BACKUP_BASE"/*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
else
    log_info "기존 프로젝트 없음 — 첫 설치"
fi

# ─── STEP 3: 기존 파일 삭제 ──────────────────────────────
log_step "STEP 3/8 기존 파일 삭제"
[ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR" && log_info "삭제 완료"

# ─── STEP 4: ZIP 압축 해제 → vm_project 로 설치 ─────────
log_step "STEP 4/8 새 버전 설치"
cd "$(dirname "$INSTALL_DIR")"
unzip -q "$ZIP_FILE"

# 압축 해제된 폴더명 확인 후 vm_project 로 rename
EXTRACTED=$(unzip -Z1 "$ZIP_FILE" | head -1 | cut -d'/' -f1)
if [ "$EXTRACTED" != "$(basename "$INSTALL_DIR")" ] && [ -d "$EXTRACTED" ]; then
    mv "$EXTRACTED" "$(basename "$INSTALL_DIR")"
    log_info "폴더 rename: $EXTRACTED → vm_project"
fi
log_info "설치 완료: $INSTALL_DIR"

# ─── STEP 5: 폴더 생성 + 권한 설정 ──────────────────────
log_step "STEP 5/8 폴더 생성 및 권한 설정"
cd "$INSTALL_DIR"
mkdir -p logs outputs/charts outputs/reports models data uploads data_lake
chmod +x scripts/*.sh 2>/dev/null || true
log_info "완료"

# ─── STEP 6: 패키지 설치 ─────────────────────────────────
log_step "STEP 6/8 Python 패키지 설치"
$PYTHON -m pip install -r requirements.txt --break-system-packages -q 2>&1 | tail -2
log_info "완료"

# ─── STEP 7: DB 시작 ─────────────────────────────────────
log_step "STEP 7/8 DB 서비스 시작"
sudo systemctl start mongod  2>/dev/null && log_info "MongoDB 시작" || log_warn "MongoDB 실패"
sudo systemctl start mariadb 2>/dev/null && log_info "MariaDB 시작" || log_warn "MariaDB 실패"

# ─── STEP 8: 서버 시작 ───────────────────────────────────
log_step "STEP 8/8 Flask 서버 시작"
nohup $PYTHON run_server.py > logs/flask.log 2>&1 &
sleep 3
curl -s http://127.0.0.1:$SERVER_PORT/api/status > /dev/null 2>&1 \
    && log_info "서버 정상 시작!" \
    || log_warn "서버 확인 실패 → tail -f logs/flask.log"

# 런처 자기 자신을 최신 버전으로 업데이트
cp "$INSTALL_DIR/scripts/launcher.sh" "$HOME/launcher.sh"
chmod +x "$HOME/launcher.sh"
log_info "런처 자동 업데이트 완료 (~/launcher.sh)"

# ─── 완료 요약 ────────────────────────────────────────────
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "VM_IP")
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║   🎉 배포 완료!                                      ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  🔢 버전:      ${GREEN}v$VERSION${NC}"
echo -e "  🌐 대시보드:  ${GREEN}http://${SERVER_IP}:$SERVER_PORT${NC}"
echo -e "  📡 API:       ${GREEN}http://127.0.0.1:$SERVER_PORT/api/status${NC}"
echo ""
echo -e "  ── 자주 쓰는 명령어 ──────────────────────────────────"
echo -e "  로그:    ${BLUE}tail -f ~/vm_project/logs/flask.log${NC}"
echo -e "  종료:    ${BLUE}sudo kill -9 \$(sudo lsof -t -i :8000)${NC}"
echo -e "  재시작:  ${BLUE}~/launcher.sh ~/vm_project_vX.X.X.zip${NC}"
echo ""
