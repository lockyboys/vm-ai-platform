"""Run four identical concurrent Ollama requests through the notebook tunnel."""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

def call(endpoint, body, timeout=145):
    data=json.dumps(body).encode()
    req=urllib.request.Request(endpoint+"/api/generate", data=data, headers={"Content-Type":"application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as r:
        return json.load(r)

def get(endpoint):
    req=urllib.request.Request(endpoint+"/api/ps")
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=10) as r:
        return json.load(r)

def one(endpoint, i):
    t=time.monotonic()
    body={"model":"gemma4:latest","prompt":"What is 12 multiplied by 13? Answer with the number only.",
          "think":False,"stream":False,"keep_alive":"5m",
          "options":{"num_ctx":2048,"num_batch":32,"num_gpu":24,"num_predict":16,
                     "temperature":0,"draft_num_predict":0}}
    r=call(endpoint,body); r["request_index"]=i; r["wall_seconds"]=round(time.monotonic()-t,3); return r

def main():
    q=json.loads(sys.stdin.read()); ep=q["endpoint"]; t=time.monotonic()
    with ThreadPoolExecutor(max_workers=4) as p:
        rs=[f.result() for f in [p.submit(one,ep,i) for i in range(1,5)]]
    print(json.dumps({"wall_seconds":round(time.monotonic()-t,3),"results":rs,"ps":get(ep)},ensure_ascii=False))

if __name__=="__main__": main()
