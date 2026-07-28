"""
Legacy Identifier Engine compatibility module.

The canonical implementation is engine.identifier_engine.IdentifierEngine.
New code must import the canonical module directly.
"""

from engine.identifier_engine import IdentifierEngine

__all__ = ["IdentifierEngine"]
