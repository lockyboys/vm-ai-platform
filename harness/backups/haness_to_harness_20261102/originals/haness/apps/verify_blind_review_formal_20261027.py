import py_compile
for p in ('/data/vm_project/config.py','/data/vm_project/haness/apps/blind_review_20261027/blind_worker.py','/data/vm_project/FastAPI/LangGraph/blind_review_worker.py'):
 py_compile.compile(p,doraise=True)
print('py_compile: PASS config, worker, formal entry')
