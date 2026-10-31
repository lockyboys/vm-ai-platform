"""Inspect only non-secret Ollama settings/status before bounded tuning probes."""
import json, urllib.request, time, sys
from pathlib import Path
import config
def main():
    result={"model":config.SPS_SOURCE_PARTNER_OLLAMA_MODEL,
            "base_url":config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL,
            "timeout":config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS}
    from langchain_ollama import ChatOllama
    result["supported_tuning_fields"]=[k for k in ChatOllama.model_fields if k in
        ("num_ctx","num_predict","keep_alive","reasoning","temperature","format","client_kwargs")]
    for endpoint in ("tags","ps"):
        start=time.monotonic()
        try:
            with urllib.request.urlopen(result["base_url"].rstrip("/")+"/api/"+endpoint,timeout=8) as response:
                result[endpoint]=json.load(response)
        except Exception as exc:
            result[endpoint]={"error_type":type(exc).__name__,"error":str(exc)[:500]}
        result[endpoint+"_seconds"]=round(time.monotonic()-start,3)
    path=Path("harness/memory/ollama_tuning_inspection_20261025.json")
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
