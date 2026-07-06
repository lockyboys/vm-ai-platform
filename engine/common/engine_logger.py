# ===========================================================
# SPS Object Runtime Engine
# ===========================================================

# [2026-07-06 17:25:31.123]
# [INFO]
# [STEP-001]
# Execution Request

# Object Code : DOCUMENT

# Status : OK
# -----------------------------------------------------------
# [STEP-002]
# Load Object Metadata

# Repository : te_story_platform

# Object Code : DOCUMENT

# Object ID : OB_20260706_00001

# Status : OK
# -----------------------------------------------------------
from datetime import datetime


class ObjectRuntimeLogger:
    """
    Object Runtime Engine Logger
    """

    def __init__(self, engine_name="Object Runtime Engine"):
        self.engine_name = engine_name

    def header(self):
        print("=" * 70)
        print(self.engine_name)
        print("=" * 70)

    def step(self, step_no, title, status="OK"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{now}]")
        print(f"[STEP-{step_no:03d}] {title}")
        print(f"STATUS : {status}")
        print("-" * 70)

    def info(self, key, value):
        print(f"{key:<25}: {value}")

    def footer(self):
        print("=" * 70)