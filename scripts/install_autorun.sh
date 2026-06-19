#!/bin/bash
# scripts/install_autorun.sh ★ 7.20.0
# 서버 자동 실행 설치 스크립트
# 초등학생 설명: 컴퓨터가 켜질 때 VM Project도 같이 켜지게 등록해요.
# DB는 지우지 않습니다. 서비스 등록만 합니다.

set -e
USER_NAME="$(whoami)"
PROJECT_DIR="$HOME/vm_project"
SERVICE_SRC="$PROJECT_DIR/deployment/systemd/vm-project.service"
SERVICE_DST="/etc/systemd/system/vm-project@.service"

echo "🧠 VM Project 자동 실행 설치"
echo "사용자: $USER_NAME"
echo "프로젝트: $PROJECT_DIR"

if [ ! -f "$SERVICE_SRC" ]; then
  echo "❌ 서비스 파일 없음: $SERVICE_SRC"
  exit 1
fi

sudo cp "$SERVICE_SRC" "$SERVICE_DST"
sudo systemctl daemon-reload
sudo systemctl enable "vm-project@$USER_NAME"
sudo systemctl restart "vm-project@$USER_NAME"

echo "✅ 자동 실행 등록 완료"
echo "상태 확인: sudo systemctl status vm-project@$USER_NAME"
echo "로그 확인: tail -f $PROJECT_DIR/logs/flask.log"
