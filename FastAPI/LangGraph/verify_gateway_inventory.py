"""직접/Gateway MCP 연결과 tools/list를 읽기 전용으로 비교한다. 토큰·세션 ID 값은 저장하지 않는다."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
REPORT=ROOT/"harness/memory/gateway_inventory_20261025.json"
def worker():
    import httpx
    from common.auth import CommonAuth
    from common.common_function import write_json_atomic,now_kst_iso
    token=CommonAuth().issue_access_token("jeaje")
    gateway=os.environ.get("SPS_MCP_OAUTH_RESOURCE_URL","").strip()
    if not gateway:
        gateway=os.environ.get("SPS_MCP_OAUTH_ISSUER_URL","").rstrip("/")+"/mcp"
    init={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"SPS-live-verification","version":"1"}}}
    evidence={"checked_at":now_kst_iso(),"state":"running","endpoints":{}}
    def decode(response):
        text=response.text
        if "text/event-stream" in response.headers.get("content-type",""):
            rows=[line[6:] for line in text.splitlines() if line.startswith("data: ")]
            return json.loads(rows[-1]) if rows else {}
        return response.json()
    with httpx.Client(timeout=15,follow_redirects=False) as client:
        for label,url in [("direct","http://127.0.0.1:8000/mcp"),("gateway",gateway)]:
            result={"url":url}
            try:
                base={"Accept":"application/json, text/event-stream","Content-Type":"application/json"}
                missing=client.post(url,json=init,headers=base)
                result["without_token_status"]=missing.status_code
                headers={**base,"Authorization":"Bearer "+token}
                response=client.post(url,json=init,headers=headers)
                result["initialize_status"]=response.status_code
                if response.status_code==200:
                    data=decode(response)
                    session=response.headers.get("Mcp-Session-Id")
                    result["session_header_present"]=bool(session)
                    if session:headers["Mcp-Session-Id"]=session
                    version=data.get("result",{}).get("protocolVersion")
                    if version:headers["MCP-Protocol-Version"]=version
                    result["protocol_version"]=version
                    result["initialized_status"]=client.post(url,json={"jsonrpc":"2.0","method":"notifications/initialized"},headers=headers).status_code
                    listed=client.post(url,json={"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}},headers=headers)
                    result["tools_list_status"]=listed.status_code
                    if listed.status_code==200:
                        payload=decode(listed)
                        names=sorted(x["name"] for x in payload.get("result",{}).get("tools",[]))
                        result["tool_count"]=len(names);result["tool_names"]=names
                        result["next_cursor_present"]=bool(payload.get("result",{}).get("nextCursor"))
                    invalid={**headers,"Mcp-Session-Id":"sps-verification-nonexistent-session"}
                    result["invalid_session_status"]=client.post(url,json={"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}},headers=invalid).status_code
                    if session:
                        try:client.delete(url,headers=headers)
                        except Exception:pass
                else:
                    result["auth_challenge_present"]=bool(response.headers.get("www-authenticate"))
                    try:result["error_message"]=decode(response).get("message","")[:180]
                    except Exception:pass
            except Exception as error:
                result["error_type"]=type(error).__name__
            evidence["endpoints"][label]=result
            write_json_atomic(REPORT,evidence)
    a=evidence["endpoints"].get("direct",{});b=evidence["endpoints"].get("gateway",{})
    evidence["inventory_matches"]=a.get("tool_names") is not None and a.get("tool_names")==b.get("tool_names")
    evidence["state"]="finished";write_json_atomic(REPORT,evidence)
if __name__=="__main__":
    if "--worker" in sys.argv:
        worker()
    else:
        with open(os.devnull,"w") as null:
            p=subprocess.Popen([sys.executable,__file__,"--worker"],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=null,stderr=null,start_new_session=True)
        print(json.dumps({"submitted":True,"pid":p.pid,"evidence_path":str(REPORT)}))
