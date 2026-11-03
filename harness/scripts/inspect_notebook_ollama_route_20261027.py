"""등록 소스의 Ollama 루프백 주소만 읽기 전용으로 점검한다. 모델 실행·설정 변경 없음."""
import json
import sys
import urllib.request
from urllib.parse import urlsplit
from common.common_function import now_kst_iso

def main():
    # 소스에서 확인한 주소를 호출자가 전달한다. 임의 외부 주소 탐색은 하지 않는다.
    request = json.loads(sys.stdin.read())
    results = []
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for base in request["endpoints"]:
        parsed = urlsplit(base)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port not in {11434,11435}:
            raise ValueError("Only observed loopback Ollama endpoints are allowed")
        row = {"endpoint":base}
        for route in ("version","tags","ps"):
            try:
                with opener.open(base+"/api/"+route,timeout=3) as response:
                    data=json.load(response)
                if route in {"tags","ps"}:
                    row[route]=[{"name":x.get("name"),"digest":x.get("digest"),"size":x.get("size"),"size_vram":x.get("size_vram")} for x in data.get("models",[])]
                else:
                    row[route]=data
            except Exception as exc:
                row[route]={"error":type(exc).__name__,"detail":str(exc)}
        results.append(row)
    print(json.dumps({"checked_at":now_kst_iso(),"read_only":True,"results":results},ensure_ascii=False))
if __name__=="__main__":
    main()
