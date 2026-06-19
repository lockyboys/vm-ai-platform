#!/bin/bash
# scripts/run_auto.sh ★ 7.12.0 — 전체 자동 시작 스크립트
echo "=============================================="
echo "🚀 VM Project 7.12.0 자동 시작"
echo "=============================================="

cd "$(dirname "$0")/.." || exit

# 필요 폴더 생성
mkdir -p logs outputs/charts outputs/reports models data uploads

# 패키지 설치
echo "📦 패키지 설치 중..."
pip install -r requirements.txt --break-system-packages -q

# DB 시작
echo "🍃 MongoDB 시작..."
sudo systemctl start mongod 2>/dev/null || echo "  MongoDB 스킵"
echo "🐬 MariaDB 시작..."
sudo systemctl start mariadb 2>/dev/null || echo "  MariaDB 스킵"

# 기존 서버 종료
sudo kill -9 $(sudo lsof -t -i :8000) 2>/dev/null || true

# Flask 서버 시작 (백그라운드)
echo "🌐 Flask 서버 시작..."
nohup python3 run_server.py > logs/flask.log 2>&1 &
sleep 3

# 서버 확인
curl -s http://127.0.0.1:8000/api/status && echo ""

# crontab 자동 등록
echo "⏰ Cron 자동 등록..."
python3 -c "from scheduler.cron_jobs import register_crontab; register_crontab()"

# 모니터링 시작
echo "🏥 모니터링 시작..."
nohup python3 monitoring/health_check.py > logs/monitor.log 2>&1 &

echo ""
echo "✅ 전체 서비스 시작 완료!"
echo "🌐 http://$(curl -s ifconfig.me 2>/dev/null || echo 'VM_IP'):8000"
echo "=============================================="
