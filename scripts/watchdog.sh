#!/bin/bash
# scripts/watchdog.sh ★ 7.20.0
# 서버 감시 스크립트
# 초등학생 설명: 서버가 잠들었는지 1분마다 확인하고, 잠들면 깨워요.

USER_NAME="$(whoami)"
URL="http://127.0.0.1:8000/api/status"
LOG="$HOME/vm_project/logs/watchdog.log"
mkdir -p "$(dirname "$LOG")"

if curl -fsS "$URL" >/dev/null 2>&1; then
  echo "$(date '+%F %T') ✅ 서버 정상" >> "$LOG"
else
  echo "$(date '+%F %T') ⚠️ 서버 응답 없음 → 재시작" >> "$LOG"
  sudo systemctl restart "vm-project@$USER_NAME" || true
fi
