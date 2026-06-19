# monitoring/health_check.py ★ 7.16.4
# ⭐ Self-Healing 자동 복구 시스템
#
# 초등학생 설명:
#   몸이 아프면 자동으로 치료하는 AI 의사 역할이에요!
#   서버(포트)가 응답 안 하면 자동으로 다시 켜줘요.
#   3번 연속 실패해야 재시작 → 일시적 오류는 그냥 넘겨요.
#
# 감시 대상:
#   flask  (8000번 포트) → AI 웹 서버
#   mongod (27017번 포트) → MongoDB DB
#   mariadb (3306번 포트) → MariaDB DB
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 감시 서비스 config로 분리
#   7.0.0  (2026-06-15): 최초 생성

import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, log_event
from config import MONITORED_SERVICES, HEALING_FAIL_THRESHOLD, HEALING_CHECK_INTERVAL


class SelfHealingSystem:
    """
    서비스 자동 복구 시스템

    초등학생 설명:
        게임에서 HP가 0이 되면 자동으로 부활하는 것처럼,
        서버가 죽으면 자동으로 다시 살려줘요!

    복구 흐름:
        포트 확인 → 응답 없음 → 실패 횟수 +1
        → 3회 이상 실패 → 서비스 재시작 명령 실행
        → 5초 대기 → 포트 재확인 → 성공/실패 로그
    """

    # 서비스별 재시작 명령어
    # 초등학생 설명: "어떻게 다시 켜야 하는지" 방법을 적어둔 매뉴얼이에요!
    RESTART_COMMANDS = {
        "flask":   "cd {project_dir} && nohup python3 run_server.py > logs/flask.log 2>&1 &",
        "mongod":  "sudo systemctl restart mongod",
        "mariadb": "sudo systemctl restart mariadb",
    }

    def __init__(self, interval: int = None):
        """
        초기화

        초등학생 설명:
            경비원이 순찰 시작 전에 준비하는 과정이에요.
            몇 초마다 확인할지, 몇 번 실패해야 재시작할지 설정해요.

        Args:
            interval : 상태 확인 주기 (초, 기본값은 config에서 가져옴)
        """
        # config.py에서 설정값 가져오기 (없으면 기본값 사용)
        self.interval  = interval or HEALING_CHECK_INTERVAL
        self.threshold = HEALING_FAIL_THRESHOLD   # 몇 번 실패해야 재시작할지
        self.services  = MONITORED_SERVICES       # 감시할 서비스 목록

        # 서비스별 연속 실패 횟수 추적
        # 초등학생 설명: 각 서버가 몇 번 연속으로 응답 안 했는지 기록해요
        self.fail_counts = {name: 0 for name in self.services}

        logger.info(f"🏥 Self-Healing 초기화 | 주기={self.interval}초 | 임계값={self.threshold}회")

    def _port_alive(self, port: int) -> bool:
        """
        특정 포트가 열려서 응답하는지 확인

        초등학생 설명:
            "문이 열려 있나요?" 확인하는 함수예요.
            열려 있으면 True, 닫혀 있으면 False를 반환해요.

        Args:
            port : 확인할 포트 번호 (예: 8000)

        Returns:
            True = 포트 열림 (서비스 정상)
            False = 포트 닫힘 (서비스 죽음)
        """
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True
        )
        return str(port) in result.stdout

    def _restart(self, name: str) -> bool:
        """
        서비스 재시작 실행

        초등학생 설명:
            꺼진 불을 다시 켜는 함수예요.
            재시작 후 5초 기다렸다가 성공했는지 확인해요.

        Args:
            name : 재시작할 서비스 이름 (flask/mongod/mariadb)

        Returns:
            True = 재시작 성공
            False = 재시작 실패
        """
        cmd  = self.RESTART_COMMANDS.get(name, "")
        port = self.services[name]

        if not cmd:
            logger.error(f"❌ {name}: 재시작 명령어 없음")
            return False

        logger.warning(f"🔧 {name} 재시작 시도 (포트: {port})")
        os.system(cmd)

        # 재시작 후 안정화 대기
        time.sleep(5)

        # 재시작 성공 여부 확인
        alive = self._port_alive(port)
        if alive:
            logger.info(f"✅ {name} 복구 성공!")
            self.fail_counts[name] = 0  # 실패 카운터 초기화
        else:
            logger.error(f"❌ {name} 복구 실패 — 수동 점검 필요")

        # DB에 복구 이력 저장
        log_event("self_healing", {
            "service": name,
            "port":    port,
            "result":  "성공" if alive else "실패",
        })
        return alive

    def monitor(self) -> None:
        """
        지속적으로 서비스 상태 감시 (무한 루프)

        초등학생 설명:
            경비원처럼 계속 순찰하면서
            이상한 게 있으면 바로 고쳐요!

        실행 방법:
            python3 monitoring/health_check.py
        """
        logger.info(f"👁️ 모니터링 시작 (감시 서비스: {list(self.services.keys())})")

        while True:
            for name, port in self.services.items():
                if not self._port_alive(port):
                    # 응답 없음 → 실패 카운터 증가
                    self.fail_counts[name] += 1
                    logger.warning(
                        f"⚠️ {name} 응답 없음 "
                        f"({self.fail_counts[name]}/{self.threshold}회)"
                    )

                    # 임계값 초과 시 재시작
                    if self.fail_counts[name] >= self.threshold:
                        self._restart(name)
                else:
                    # 정상 응답 → 실패 카운터 초기화
                    if self.fail_counts[name] > 0:
                        logger.info(f"💚 {name} 정상 복귀")
                    self.fail_counts[name] = 0

            # 다음 확인까지 대기
            time.sleep(self.interval)


if __name__ == "__main__":
    # 직접 실행 시 모니터링 시작
    # 사용법: python3 monitoring/health_check.py
    SelfHealingSystem().monitor()
