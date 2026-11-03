"""Run two identical concurrent Ollama requests through the notebook tunnel."""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

def post(endpoint, body, timeout=145):
    data = json.dumps(body).encode()
    req = urllib.request.Request(endpoint + "/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as r:
        return json.load(r)

def get(endpoint, route):
    req = urllib.request.Request(endpoint + "/api/" + route)
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as r:
        return json.load(r)

def one(endpoint, index):
    started = time.monotonic()
    body = {"model":"gemma4:latest","prompt":"What is 12 multiplied by 13? Answer with the number only.",
            "think":False,"stream":False,"keep_alive":"5m",
            "options":{"num_ctx":2048,"num_batch":32,"num_gpu":24,
                       "num_predict":16,"temperature":0,"draft_num_predict":0}}
    result = post(endpoint, body)
    result["request_index"] = index
    result["wall_seconds"] = round(time.monotonic() - started, 3)
    return result

def main():
    q = json.loads(sys.stdin.read())
    endpoint = q["endpoint"]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(one, endpoint, i) for i in (1,2)]
        results = [f.result() for f in futures]
    print(json.dumps({"started_at":started,"wall_seconds":round(time.monotonic()-started,3),
                      "results":results,"ps":get(endpoint,"ps")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
