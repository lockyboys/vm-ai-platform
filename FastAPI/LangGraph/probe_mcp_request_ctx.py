"""(임시 점검용) 설치된 mcp 라이브러리에서 요청 컨텍스트(clientInfo) 접근 경로를 확인한다.

목적: source_audit 래퍼에서 호출 클라이언트 이름을 로그로 남기기 전에, 어떤 import 경로가
      실제로 존재하는지 확인한다. 네트워크·DB·파일 쓰기 없음, 표준출력만 사용.
"""
import importlib
import importlib.metadata
import json

result = {}
try:
    result["mcp_version"] = importlib.metadata.version("mcp")
except Exception as error:  # 버전 조회 실패도 그대로 보고
    result["mcp_version"] = f"unknown: {type(error).__name__}"

# 후보 경로: 저수준 서버의 요청 컨텍스트 ContextVar
for module_name, attribute in (("mcp.server.lowlevel.server", "request_ctx"),
                               ("mcp.shared.context", "RequestContext")):
    try:
        module = importlib.import_module(module_name)
        result[f"{module_name}.{attribute}"] = hasattr(module, attribute)
    except Exception as error:
        result[f"{module_name}.{attribute}"] = f"import error: {type(error).__name__}"

# ServerSession이 client_params 속성을 갖는지(초기화 시 clientInfo가 저장되는 곳)
try:
    from mcp.server.session import ServerSession
    result["ServerSession.client_params"] = "client_params" in dir(ServerSession)
except Exception as error:
    result["ServerSession.client_params"] = f"import error: {type(error).__name__}"

print(json.dumps(result, ensure_ascii=False))
