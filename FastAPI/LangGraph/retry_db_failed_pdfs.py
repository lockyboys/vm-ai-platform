"""저장된 실패 PDF만 격리 폴더에 재시도한다. 기존 PDF·상태·실패 목록은 보존한다."""
import json,sys
from pathlib import Path
ROOT=Path("/data/vm_project");sys.path.insert(0,str(ROOT))
from common.common_function import now_kst_iso,write_json_atomic,validate_safe_pdf_filename
from FastAPI.LangGraph.Agent_Import_PFDs import public_document_catalog_collector as c
profile=c.load_profile("db_insurance_terms")
out=c.output_dir(profile)
failed=json.loads((out/"failures.json").read_text())
print(json.dumps({"dry_run":True,"retry_count":len(failed),"files":[r["file"] for r in failed]},ensure_ascii=False))
if sys.stdin.read().strip()=="RETRY FAILED PDFS":
    retry=out/("retry_"+now_kst_iso().replace(":","").replace("-","").replace("+","_"))
    retry.mkdir(parents=True,exist_ok=False)
    client=c.SiteClient(profile)
    results=[]
    for row in failed:
        name=validate_safe_pdf_filename(row["file"])
        url=c.render(profile["document"]["url_template"],{profile["document"]["file_var"]:name})
        try:
            info=client.download(url,retry/name)
            result={"file":name,"status":"verified",**info}
        except Exception as error:
            result={"file":name,"status":"failed","error_type":type(error).__name__,"error":str(error)[:200]}
        results.append(result)
    evidence={"checked_at":now_kst_iso(),"results":results,"success":sum(r["status"]=="verified" for r in results),"failed":sum(r["status"]=="failed" for r in results),"original_files_preserved":True}
    write_json_atomic(retry/"verification.json",evidence)
    write_json_atomic(ROOT/"harness/memory/db_failed_pdf_retry_20261025.json",evidence)
    print(json.dumps(evidence,ensure_ascii=False))
