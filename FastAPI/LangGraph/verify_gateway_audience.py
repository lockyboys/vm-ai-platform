"""OAuth audience의 정상/오류 토큰을 실제 MCP 초기화 요청으로 검증한다. 토큰 값은 보존하지 않는다."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
REPORT=ROOT/"harness/memory/gateway_audience_20261025.json"
def worker():
    import httpx
    from common.auth import CommonAuth
    from common.common_function import now_kst_iso,write_json_atomic
    auth=CommonAuth();issuer=os.environ["SPS_MCP_OAUTH_ISSUER_URL"].rstrip("/")
    resource=os.getenv("SPS_MCP_OAUTH_RESOURCE_URL",issuer+"/mcp").rstrip("/")
    scopes=os.getenv("SPS_MCP_OAUTH_SCOPES","mcp:tools")
    now=int(time.time());result={"checked_at":now_kst_iso(),"issuer":issuer,"expected_audience":resource,"checks":[]}
    with httpx.Client(timeout=12) as client:
        for label,url in [("direct","http://127.0.0.1:8000/mcp"),("gateway",resource)]:
            for case,audience in [("correct_audience",resource),("wrong_audience","https://invalid.example/mcp")]:
                # OAuth와 같은 mcp_$access 용도 및 필수 claims를 사용하고 audience만 바꾼다.
                token=auth.issue_token("sps-audience-probe",token_type="mcp_$access",expires_in=90,issued_at=now,
                    additional_claims={"iss":issuer,"aud":audience,"client_id":"sps-audience-verification","scope":scopes,"token_use":"access","nbf":now})
                headers={"Authorization":"Bearer "+token,"Accept":"application/json, text/event-stream"}
                try:
                    r=client.post(url,headers=headers,json={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"audience-probe","version":"1"}}})
                    result["checks"].append({"endpoint":label,"case":case,"http_status":r.status_code,"verified":r.status_code==(200 if case=="correct_audience" else 401)})
                    session=r.headers.get("Mcp-Session-Id")
                    if session:
                        try:client.delete(url,headers={**headers,"Mcp-Session-Id":session})
                        except Exception:pass
                except Exception as e:result["checks"].append({"endpoint":label,"case":case,"error_type":type(e).__name__,"verified":False})
                write_json_atomic(REPORT,result)
    result["finished"]=True;result["verified"]=all(x["verified"] for x in result["checks"]);write_json_atomic(REPORT,result)
if __name__=="__main__":
    if "--worker" in sys.argv:worker()
    else:
        with open(os.devnull,"w") as null:p=subprocess.Popen([sys.executable,__file__,"--worker"],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=null,stderr=null,start_new_session=True)
        print(json.dumps({"submitted":True,"pid":p.pid,"evidence_path":str(REPORT)}))
