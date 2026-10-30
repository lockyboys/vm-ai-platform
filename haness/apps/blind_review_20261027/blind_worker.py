"""SPS-launched blind inference. This worker reads inputs, never the private key/tests.
Each provider sees a fresh user message only. It cannot call repository tools.
Raw responses and actual timestamps are persisted after every independent call.
"""
import os,json,sys,time,hashlib,urllib.request,urllib.error,base64,zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from config import OLLAMA_ENDPOINT, OLLAMA_MODEL, OLLAMA_NUM_GPU, OLLAMA_NUM_CTX, OLLAMA_NUM_BATCH, OLLAMA_NUM_PREDICT, OLLAMA_TEMPERATURE, OLLAMA_KEEP_ALIVE, OLLAMA_WORKERS, OLLAMA_TIMEOUT_SECONDS
ROOT=Path(__file__).resolve().parent
PROMPT='이 프로그램을 검토해 주세요.'
OPTIONS={'num_ctx':OLLAMA_NUM_CTX,'num_batch':OLLAMA_NUM_BATCH,'num_gpu':OLLAMA_NUM_GPU,'num_predict':OLLAMA_NUM_PREDICT,'temperature':OLLAMA_TEMPERATURE}
DIGEST='dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c'
DEFAULT_OLLAMA_WORKERS=OLLAMA_WORKERS
def now():return datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
def save(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.replace(path)
def request(route,data=None,timeout=10):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 req=urllib.request.Request(OLLAMA_ENDPOINT+'/api/'+route,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 with opener.open(req,timeout=timeout) as r:return json.load(r)

# ---- 2026-10-30 보고서 대책 반영 (원문 보존 / summary 재생성 / 82건 완료 게이트) ----
def tunnel_alive():
 """SSH 역방향 터널 생존 확인. /api/version 이 응답하면 True.
 연속 실패로 중단될 때 '모델 실패'와 '연결 단절'을 구분해 기록하기 위해 쓴다."""
 try:
  request('version',timeout=5);return True
 except Exception:
  return False
def reusable_result(path):
 """이미 저장된 결과를 재사용할지 판단한다.
 - success=true 인 결과만 재사용(dict 반환)
 - 실패/손상 결과는 지우지 않고 <id>.attemptN.json 으로 옮겨 보존한 뒤 None(재실행) 반환
 이전 코드는 파일이 존재만 하면 건너뛰어, 실패 건이 영원히 재시도되지 않았다."""
 if not path.exists():return None
 try:
  r=json.loads(path.read_text())
  if r.get('success') is True:return r
 except (json.JSONDecodeError,OSError):
  pass
 n=1
 while path.with_name(f'{path.stem}.attempt{n}.json').exists():n+=1
 path.replace(path.with_name(f'{path.stem}.attempt{n}.json'))
 return None
def finalize_summary(summary,out,inputs):
 """summary 를 '현재 실행분 카운터'가 아니라 고유 결과 파일 기준으로 재생성한다.
 completed  : 입력 ID 중 success=true 결과 파일이 있는 고유 ID 수
 total      : 입력 건수 (82)
 unique_ids : 입력의 고유 ID 수 (중복 ID 가 있으면 total 과 달라져 완료 불가)
 status     : running 이었던 경우에만 completed/incomplete 로 확정 (blocked/preflight 실패는 유지)"""
 ids=[i['id'] for i in inputs];runs=[]
 for item_id in dict.fromkeys(ids):
  p=out/(item_id+'.json')
  if not p.exists():continue
  try:r=json.loads(p.read_text())
  except (json.JSONDecodeError,OSError):continue
  runs.append({k:r.get(k) for k in ('id','started_at','finished_at','elapsed_seconds','success')})
 completed=sum(1 for r in runs if r['success'] is True)
 summary.update(runs=runs,completed=completed,total=len(ids),unique_ids=len(set(ids)))
 if summary.get('status')=='running':
  ok=len(ids)>0 and completed==len(ids)==len(set(ids))
  summary['status']='completed' if ok else 'incomplete'
 return summary
def job_output_dir(provider,job_id):
 """job 별 결과 디렉터리. job_id 가 없으면(구 호출) 기존 공용 경로를 쓴다.
 job 간 결과 파일이 섞여 summary 와 파일 수가 어긋나던 문제를 막는다."""
 base=ROOT/'results'/provider
 if not job_id:return base
 if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):raise ValueError('Invalid job_id')
 return base/'jobs'/job_id
def main():
 args=json.loads(sys.stdin.read());provider=args['provider'];assert provider in ('ollama','gemini')
 ollama_workers=max(1,int(args.get('ollama_workers',os.getenv('OLLAMA_WORKERS',DEFAULT_OLLAMA_WORKERS))))
 input_bytes=zlib.decompress(base64.b64decode((ROOT/'blind_inputs.b64').read_text()))
 inputs=json.loads(input_bytes)
 out=job_output_dir(provider,args.get('job_id'));out.mkdir(parents=True,exist_ok=True)
 summary={'provider':provider,'started_at':now(),'status':'running','completed':0,'total':len(inputs),'prompt':PROMPT,'input_sha256':hashlib.sha256(input_bytes).hexdigest(),'ollama_workers':ollama_workers if provider=='ollama' else 1,'runs':[]}
 save(out/'summary.json',summary)
 try:
  if provider=='ollama':
   summary['version']=request('version');tags=request('tags')
   m=next(m for m in tags['models'] if m['name']==OLLAMA_MODEL)
   assert m['digest']==DIGEST,'Notebook model fingerprint mismatch'
   summary['model']=OLLAMA_MODEL;summary['options']=OPTIONS
  else:
   from dotenv import load_dotenv
   load_dotenv('/data/vm_project/.env',override=False)
   from langchain_google_genai import ChatGoogleGenerativeAI
   from pydantic import SecretStr
   key=os.getenv('GEMINI_API_KEY','').strip() or os.getenv('GOOGLE_API_KEY','').strip()
   if not key:raise ValueError('Gemini credential absent in worker environment')
   summary['model']=os.getenv('GEMINI_MODEL','gemini-2.5-flash').strip()
   llm=ChatGoogleGenerativeAI(model=summary['model'],api_key=SecretStr(key),temperature=0,max_output_tokens=4096,thinking_budget=0,max_retries=0,timeout=OLLAMA_TIMEOUT_SECONDS)
  save(out/'summary.json',summary)
  failures=0
  summary_lock=threading.Lock()
  stop_event=threading.Event()

  def process_item(item):
   path=out/(item['id']+'.json')
   # 성공 결과만 재사용, 실패 결과는 attempt 파일로 보존 후 재실행
   prev=reusable_result(path)
   if prev is not None:return prev
   r={'id':item['id'],'started_at':now(),'source_sha256':hashlib.sha256(item['source'].encode()).hexdigest()};start_time=time.monotonic()
   message=PROMPT+'\\n\\n\`\`\`javascript\\n'+item['source']+'\\n\`\`\`';r['message_sha256']=hashlib.sha256(message.encode()).hexdigest()
   try:
    if provider=='ollama':
     raw=request('chat',{'model':summary['model'],'messages':[{'role':'user','content':message}],'stream':False,'think':False,'options':OPTIONS,'keep_alive':OLLAMA_KEEP_ALIVE},timeout=29900)
     r['response']=raw.get('message',{}).get('content','');r['raw']=raw;r['success']=raw.get('done') is True and not raw.get('error') and bool(r['response']);r['truncated']=raw.get('done_reason')=='length'
    else:
     raw=llm.invoke(message);r['response']=raw.content if isinstance(raw.content,str) else '\\n'.join(x.get('text','') for x in raw.content if isinstance(x,dict));r['metadata']=raw.response_metadata;r['usage']=raw.usage_metadata;r['success']=bool(r['response']);r['truncated']=raw.response_metadata.get('finish_reason') in ('MAX_TOKENS','LENGTH')
   except urllib.error.HTTPError as e:r.update(success=False,error='HTTP '+str(e.code)+': '+e.read().decode(errors='replace'))
   except Exception as e:r.update(success=False,error=type(e).__name__+': '+str(e))
   r['elapsed_seconds']=round(time.monotonic()-start_time,3);r['finished_at']=now();save(path,r);return r

  # 성공 결과가 없는 항목만 대기열에 넣는다 (실패 결과는 여기서 attempt 로 보존됨)
  pending=[item for item in inputs if reusable_result(out/(item['id']+'.json')) is None]
  if provider=='ollama':
   with ThreadPoolExecutor(max_workers=ollama_workers) as pool:
    futures={pool.submit(process_item,item):item for item in pending}
    for future in as_completed(futures):
     r=future.result()
     with summary_lock:
      summary['runs'].append({k:r[k] for k in ('id','started_at','finished_at','elapsed_seconds','success')});summary['completed']+=1
      failures=failures+1 if not r['success'] else 0;save(out/'summary.json',summary)
     if failures>=3:
      stop_event.set();summary['status']='blocked_after_3_consecutive_failures'
      # 연결 단절(터널)인지 모델 응답 실패인지 구분해 기록
      summary['tunnel_alive']=tunnel_alive()
      for other in futures:
       if other is not future:other.cancel()
      break
  else:
   for item in pending:
    r=process_item(item);summary['runs'].append({k:r[k] for k in ('id','started_at','finished_at','elapsed_seconds','success')});summary['completed']+=1;failures=failures+1 if not r['success'] else 0;save(out/'summary.json',summary)
    if failures>=3:
     summary['status']='blocked_after_3_consecutive_failures';break
  # 진행 중 카운터 대신 고유 결과 파일 기준으로 summary 를 재생성하고 82건 게이트로 상태 확정
  finalize_summary(summary,out,inputs)
 except Exception as e:summary.update(status='preflight_failed',error=type(e).__name__+': '+str(e))
 summary['finished_at']=now();save(out/'summary.json',summary)
 print(json.dumps({k:v for k,v in summary.items() if k!='runs'},ensure_ascii=False))
if __name__=='__main__':main()
