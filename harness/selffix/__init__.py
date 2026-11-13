"""스스로 고치는 앱(self-fixing) 공통 패키지 (2026-11-12, LuckyBoys 결정: harness/selffix/ 한 곳으로 분리).

모듈 지도 — 역할 단위로 나눴다(한 파일에 섞여 있던 531줄 엔진을 쪼갬)
    job_runner   : 백그라운드 job 공통(경로 검사·KST 시각·systemctl 상태 조회)
    target_spec  : [입력·검증] 자기 수리 대상 스펙/파라미터 검증
    runner       : [실행·판정] 대상 실행과 성공 기준(verdict) 판정
    repair_loop  : [수리] 실패 → 수리 체인 → 재실행 루프와 증빙 저장
    registry     : [등록] config.py 표시 블록 등록소(repository 백엔드는 2차 DDL 승인 전)
기존 진입점 harness.mcp.agents.self_repair_engine 은 MCP 도구와 worker 만 남기고 위 모듈을 다시 내보낸다
(외부 import·서버 등록은 바꾸지 않는다).
"""
