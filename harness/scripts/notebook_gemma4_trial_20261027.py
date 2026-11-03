"""승인된 노트북 Gemma4 단일 시험. 노트북 모델 지문 확인 후 요청별 옵션만 적용한다."""
import json
import sys
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from common.common_function import now_kst_iso, write_json_atomic

def main():
    request = json.loads(sys.stdin.read())
    if request.get("endpoint") != "http://127.0.0.1:11435":
        raise ValueError("Only the verified notebook tunnel is allowed")
    endpoint = request["endpoint"]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def read(route, body=None, timeout=5):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(endpoint+"/api/"+route, data=data,
            headers={"Content-Type":"application/json"})
        with opener.open(req,timeout=timeout) as response:
            return json.load(response)
    report = {"started_at":now_kst_iso(),"model":"gemma4:latest","options":request["options"],"success":False}
    started = time.monotonic()
    try:
        # 동일 이름의 서버 모델을 잘못 실행하지 않도록 전체 digest를 대조한다.
        version = read("version")
        tags = read("tags")
        model = next(x for x in tags["models"] if x["name"] == report["model"])
        if version.get("version") != "0.40.11" or model["digest"] != request["expected_digest"]:
            raise ValueError("Notebook fingerprint changed; refusing generation")
        report["version"] = version
        report["digest"] = model["digest"]
        report["response"] = read("generate",{"model":report["model"],
            "prompt":"What is 12 multiplied by 13? Answer with the number only.",
            "stream":False,"think":False,"options":request["options"],"keep_alive":"5m"},
            timeout=29980)
        result = report["response"]
        report["success"] = result.get("done") is True and not result.get("error")
        report["arithmetic_correct"] = result.get("response","").strip() == "156"
        if result.get("eval_duration",0)>0:
            report["tokens_per_second"] = result["eval_count"]*1e9/result["eval_duration"]
    except urllib.error.HTTPError as exc:
        report["http_status"] = exc.code
        report["error"] = exc.read().decode(errors="replace")
    except Exception as exc:
        report["error"] = type(exc).__name__+": "+str(exc)
    try:
        report["ps"] = read("ps")
    except Exception as exc:
        report["ps_error"] = str(exc)
    report["elapsed_seconds"] = round(time.monotonic()-started,3)
    report["finished_at"] = now_kst_iso()
    path = Path("harness/memory/notebook_ollama_trials")/(uuid.uuid4().hex+".json")
    # 원자 저장 공통함수는 부모 폴더를 만들지 않으므로 호출 전에 생성한다.
    path.parent.mkdir(parents=True,exist_ok=True)
    write_json_atomic(path,report)
    print(json.dumps({"report_path":str(path),**report},ensure_ascii=False))
if __name__=="__main__":
    main()
