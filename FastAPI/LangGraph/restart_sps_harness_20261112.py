"""2026-11-12 LuckyBoys 승인: sps-harness.service 재시작 (소스 리뷰 Tavily 끄기(선택 B) 반영용).

왜 바로 restart하지 않고 systemd-run 타이머로 5초 뒤에 하나:
  이 스크립트는 sps-harness MCP 서버가 띄운 자식 프로세스다. 바로 restart하면 서버와 함께
  이 스크립트도 종료되어 결과를 돌려주지 못한다. 그래서 별도 일회성 유닛이 5초 뒤에
  'systemctl restart sps-harness.service'를 실행하게 예약하고, 예약 결과만 즉시 출력한다.
  (2026-11-02 restart_sps_harness_20261102.py와 같은 방식, 유닛 이름만 날짜를 바꿔 충돌 방지)
실행 명령(승인 대상):
  sudo -n systemd-run --on-active=5 --unit=sps-harness-restart-20261112 /usr/bin/systemctl restart sps-harness.service
"""
import json
import subprocess

COMMAND = ["sudo", "-n", "systemd-run", "--on-active=5", "--unit=sps-harness-restart-20261112",
           "/usr/bin/systemctl", "restart", "sps-harness.service"]

completed = subprocess.run(COMMAND, capture_output=True, text=True, timeout=20, check=False)
print(json.dumps({"command": COMMAND, "returncode": completed.returncode,
                  "stdout": completed.stdout[-1000:], "stderr": completed.stderr[-1000:]},
                 ensure_ascii=False))
