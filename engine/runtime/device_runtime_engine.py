"""
Device Runtime Engine

Purpose:
    Detect runtime execution environment.
    Decide CPU/GPU execution mode.
    Provide common device context for OCR, Video, Audio, LLM engines.
"""

import os
import platform
import sys
import json
from datetime import datetime


class DeviceRuntimeEngine:
    def __init__(self):
        self.detected_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def detect(self):
        torch_info = self._detect_torch()
        system_info = self._detect_system()

        gpu_available_yn = "Y" if torch_info.get("cuda_available_yn") == "Y" else "N"
        execution_device = "GPU" if gpu_available_yn == "Y" else "CPU"

        return {
            "detected_dt": self.detected_dt,
            "execution_device": execution_device,
            "gpu_available_yn": gpu_available_yn,
            **system_info,
            **torch_info,
            "capability": {
                "supports_easyocr": gpu_available_yn == "Y",
                "supports_pytorch": torch_info.get("torch_installed_yn") == "Y",
                "supports_whisper": gpu_available_yn == "Y",
                "supports_embedding": torch_info.get("torch_installed_yn") == "Y",
                "supports_llm": gpu_available_yn == "Y",
            },
        }

    def _detect_system(self):
        return {
            "os_name": platform.system(),
            "os_version": platform.version(),
            "platform_name": platform.platform(),
            "python_version": sys.version.split()[0],
            "cpu_count": os.cpu_count(),
        }

    def _detect_torch(self):
        try:
            import torch

            cuda_available = torch.cuda.is_available()
            gpu_name = None
            gpu_count = 0
            cuda_version = torch.version.cuda

            if cuda_available:
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)

            return {
                "torch_installed_yn": "Y",
                "torch_version": torch.__version__,
                "cuda_available_yn": "Y" if cuda_available else "N",
                "cuda_version": cuda_version,
                "gpu_count": gpu_count,
                "gpu_name": gpu_name,
            }

        except Exception as e:
            return {
                "torch_installed_yn": "N",
                "torch_version": None,
                "cuda_available_yn": "N",
                "cuda_version": None,
                "gpu_count": 0,
                "gpu_name": None,
                "torch_error_message": str(e),
            }


if __name__ == "__main__":
    engine = DeviceRuntimeEngine()
    result = engine.detect()
    print(json.dumps(result, ensure_ascii=False, indent=2))