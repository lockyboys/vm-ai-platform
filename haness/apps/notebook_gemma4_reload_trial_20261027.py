"""Reload Gemma4 with lower context/batch and measure placement."""
import json,sys,time,uuid,urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
def now(): return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
def post(endpoint,body,timeout=29980):
 data=json.dumps(body).encode();req=urllib.request.Request(endpoint+"/api/generate",data=data,headers={"Content-Type":"application/json"})
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=timeout) as r:return json.load(r)
def get(endpoint,route):
 req=urllib.request.Request(endpoint+"/api/"+route)
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=10) as r:return json.load(r)
def main():
 q=json.loads(sys.stdin.read()); ep=q["endpoint"]; started=now()
 # Unload the currently resident runner through the API; no files or server settings change.
 unload=post(ep,{"model":"gemma4:latest","prompt":"","stream":False,"keep_alive":0},120)
 t=time.monotonic()
 result=post(ep,{"model":"gemma4:latest","prompt":"What is 12 multiplied by 13? Answer with the number only.","stream":False,"think":False,"keep_alive":"5m","options":{"num_ctx":1024,"num_batch":16,"num_gpu":99,"num_predict":64,"temperature":0,"draft_num_predict":0}},29980)
 result["elapsed_seconds"]=round(time.monotonic()-t,3);result["started_at"]=started;result["finished_at"]=now();result["unload"]=unload;result["ps"]=get(ep,"ps")
 print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
