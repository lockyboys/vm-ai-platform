#!/bin/bash
# scripts/install_watchdog_cron.sh ★ 7.20.0
# watchdog cron 등록
# 초등학생 설명: 서버 건강검진 알람을 매분 울리게 등록해요.

LINE="* * * * * $HOME/vm_project/scripts/watchdog.sh"
(crontab -l 2>/dev/null | grep -v 'vm_project/scripts/watchdog.sh'; echo "$LINE") | crontab -
echo "✅ Watchdog cron 등록 완료"
crontab -l | grep watchdog || true
