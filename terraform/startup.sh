#!/bin/bash
# terraform/startup.sh ★ 7.12.0
# GCP VM 시작 시 자동 설치 스크립트

echo "🚀 VM Project 7.12.0 자동 설치 시작"

apt-get update && apt-get install -y python3.10 python3-pip git

# Docker 설치
curl -fsSL https://get.docker.com | sh
systemctl start docker && systemctl enable docker

# 프로젝트 설치
cd /home && git clone https://github.com/your-username/vm_project_7.12.0.git
cd vm_project_7.12.0
pip3 install -r requirements.txt --break-system-packages

# 서버 시작
chmod +x scripts/run_auto.sh && ./scripts/run_auto.sh

echo "✅ 설치 완료!"
