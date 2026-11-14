"""Compatibility entry point; use blind_review_worker.py for new jobs."""
import runpy
runpy.run_path("/data/vm_project/haness/apps/blind_review_20261027/blind_worker.py",run_name="__main__")
