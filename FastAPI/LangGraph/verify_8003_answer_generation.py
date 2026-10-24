"""실제 운영 8003 API의 답변 생성·기억 저장·동일 요청 재조회를 검증한다."""
import datetime, json, re, sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4
ROOT=Path("/data/vm_project")
sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from common.auth import CommonAuth

def main():
    # 서비스와 동일한 보호 키를 사용하되 토큰과 비밀값은 출력하거나 저장하지 않는다.
    settings=dotenv_values("/etc/sps-harness/secrets.env")
    auth=CommonAuth(secret_key=settings["SPS_AUTH_JWT_SECRET_KEY"],
                    jwt_expire_seconds=180,refresh_token_expire_seconds=300)
    marker=uuid4().hex[:12]
    subject="service-8003-verification-"+marker
    request_id="answer-8003-"+marker
    payload={"query":"실제 API 동작 검증입니다. 웹 검색이나 외부 도구 없이 17 더하기 25를 계산하고, 답은 숫자만 출력하세요.",
             "thread_id":request_id,"request_id":request_id,"calendar_results":[],"gmail_results":[]}
    token=auth.issue_access_token(subject)
    headers={"Content-Type":"application/json","Accept":"application/json","Authorization":"Bearer "+token}
    def call():
        req=Request("http://127.0.0.1:8003/api/agent/context",
                    data=json.dumps(payload,ensure_ascii=False).encode(),headers=headers,method="POST")
        try:
            with urlopen(req,timeout=85) as response:
                return response.status,json.load(response)
        except HTTPError as error:
            data=json.load(error)
            return error.code,{"detail":data.get("detail")}
    http,result=call()
    answer=result.get("response","")
    verified=http==200 and result.get("status")=="success" and re.search(r"\b42\b",answer) is not None and result.get("memory_saved") is True
    # 같은 request_id를 재전송하면 생성된 답변이 저장소에서 동일하게 복원돼야 한다.
    replay_http,replay=call() if verified else (None,{})
    replay_ok=verified and replay_http==200 and replay.get("response")==answer and replay.get("memory_saved") is True
    evidence={"checked_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
              "endpoint":"http://127.0.0.1:8003/api/agent/context","subject_id":subject,"request_id":request_id,
              "question":payload["query"],"http_status":http,"response":answer,"memory_saved":result.get("memory_saved"),
              "detail":result.get("detail"),"replay_http_status":replay_http,"stored_response_replayed":replay_ok,
              "verified":bool(replay_ok)}
    out=ROOT/"harness/memory"/(request_id+".json")
    out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({**evidence,"evidence_path":str(out)},ensure_ascii=False))
    raise SystemExit(0 if replay_ok else 1)
if __name__=="__main__":
    main()
