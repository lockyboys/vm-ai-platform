"""Renamed AIA PDFs' total size, read only."""
import json
from pathlib import Path
folder=Path("/data/vm_project/outputs/insurance_docs/AIA/first_page_named")
names=json.loads("[\"무배당  프라임평생설계보험.pdf\",\"무배당  프라임평생설계보험5.pdf\",\"무배당  프라임평생설계보험6.pdf\",\"무배당  프라임평생설계보험  약관.pdf\",\"무배당 시니어보장플랜5.pdf\",\"무배당 시니어보장플랜.pdf\",\"무배당 시니어보장플랜2.pdf\",\"무배당 시니어보장플랜3.pdf\",\"무배당 시니어보장플랜4.pdf\",\"무배당  AIG  프라임종신의료비보장보험( 건강관리형,   순수보장형).pdf\",\"무배당  AAA교통상해보험2.pdf\",\"무배당  AAA교통상해보험.pdf\",\"무배당  어린이의료비보장보험.pdf\",\"무배당  어린이의료비보장보험2.pdf\",\"무배당  어린이의료비보장보험3.pdf\",\"무배당  AIG상해보험.pdf\",\"무배당  AIG상해보험7.pdf\",\"무배당  AIG상해보험2.pdf\",\"무배당  AIG상해보험3.pdf\",\"무배당  AIG상해보험4.pdf\",\"무배당  AIG상해보험5.pdf\",\"무배당  AIG상해보험6.pdf\",\"무배당  AIG  다보장의료보험.pdf\",\"무배당  AIG YES  실버  종신보험.pdf\",\"무배당  AIG  마이웨이  종신보험.pdf\",\"무배당  AIG YES  실버  보험.pdf\",\"무배당  AIG YES  실버  보험2.pdf\",\"무배당  AIG  마이웨이  정기보험.pdf\",\"무배당  프라임평생설계보험7.pdf\",\"무배당  프라임평생설계보험4.pdf\",\"무배당 AIG대중교통상해보험.pdf\",\"무배당 AIG대중교통상해보험2.pdf\"]")
sizes=[(name,(folder/name).stat().st_size) for name in names]
allpdf=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower()==".pdf"]
print(json.dumps({"renamed_count":len(sizes),"renamed_bytes":sum(n for _,n in sizes),
"all_pdf_count":len(allpdf),"all_pdf_bytes":sum(p.stat().st_size for p in allpdf),
"smallest":min(sizes,key=lambda x:x[1]),"largest":max(sizes,key=lambda x:x[1])},ensure_ascii=False))
