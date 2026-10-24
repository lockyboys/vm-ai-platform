"""SPS 실행 도구의 허용 경로에서 haness 읽기 전용 진단을 호출하는 진입점입니다."""

from haness.mcp.tools.email_rag_live_diagnostics import main


if __name__ == "__main__":
    # 진단 구현은 haness에 유지하고 이 파일은 실행 경로 제한만 연결합니다.
    main()
