"""
SPS Object Definition Engine

Purpose:
    Object Definition Request를 검증하고 다음 Repository를 생성한다.

    - sp_object
    - sp_identifier_sequence

Principles:
    - Repository First
    - Object First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""

# Change History
# 20260912 | Codex | #24: 중복 실행·채번 구현을 제거하고 공통 Engine을 재사용한다.
# 구형 import 경로는 유지하되, 실행 정책은 패키지 Engine 한 곳에서만 관리한다.
from engine.object_definition.engine import ObjectDefinitionEngine

__all__ = ["ObjectDefinitionEngine"]
