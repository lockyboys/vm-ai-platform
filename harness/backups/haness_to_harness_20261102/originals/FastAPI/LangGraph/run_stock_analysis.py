"""SPS 실행 도구에서 쓰는 진입점. 기본 실행은 네트워크 없는 dry-run입니다."""
import os
from pathlib import Path
import sys

# 하위 경로에서 직접 실행해도 프로젝트 공통 설정/함수를 재사용합니다.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dotenv import dotenv_values
import config

# 보호된 파일에서는 이 기능의 두 값만 메모리에 로드합니다. 값은 출력/저장하지 않습니다.
for filename in (ROOT / '.env', Path(config.SPS_MCP_WORKER_SECRETS_FILE)):
    try:
        values = dotenv_values(filename) if filename.is_file() else {}
    except (OSError, PermissionError):
        values = {}
    for name in (config.STOCK_ANALYSIS['kis_app_key_env'], config.STOCK_ANALYSIS['kis_app_secret_env']):
        if not os.getenv(name) and values.get(name):
            os.environ[name] = values[name]

from haness.stock_analysis import main
if __name__ == '__main__':
    main()
