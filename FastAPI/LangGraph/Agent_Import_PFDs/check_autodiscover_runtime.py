"""자동 탐색(브라우저 기반) 실행 환경 점검(읽기 전용).

서버에 Playwright와 Chromium이 있는지만 확인한다. 설치·변경은 하지 않는다.
"""

import importlib.util
import json
import shutil
import subprocess
import sys

result = {"python": sys.version.split()[0], "playwright_module": bool(importlib.util.find_spec("playwright"))}
for name in ("chromium", "chromium-browser", "google-chrome"):
    result[name] = shutil.which(name)
if result["playwright_module"]:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            result["chromium_launch"] = "ok"
            browser.close()
    except Exception as error:  # 점검용: 원인 문자열만 보고
        result["chromium_launch"] = f"failed: {error.__class__.__name__}: {str(error)[:300]}"
pip = subprocess.run([sys.executable, "-m", "pip", "show", "playwright"], capture_output=True, text=True)
result["pip_show_playwright"] = pip.stdout.strip()[:300]
print(json.dumps(result, ensure_ascii=False, indent=1))
