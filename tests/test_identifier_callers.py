"""IdentifierEngine caller contract regression tests."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

from engine.identifier_engine import IdentifierEngine
from core.identifier.identifier_engine import IdentifierEngine as LegacyIdentifierEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CALLER_CONTRACTS = {
    "engine/batch/business_domain_repository_sync_batch.py": {
        "generate",
    },
    "engine/generator/erd_generator.py": {
        "generate",
        "generate_for_level",
    },
    "engine/generator/metadata_generator.py": {
        "generate_for_level",
    },
    "engine/generator/relationship_generator.py": {
        "generate_for_level",
    },
    "engine/object_definition_engine.py": {
        "render_identifier",
    },
    "engine/object_definition/identifier_workflow_legacy.py": {
        "render_identifier",
    },
    "engine/processor/work/file_work_service.py": {
        "generate",
    },
    "engine/runtime/object_runtime_engine.py": {
        "generate",
    },
    "tools/register_column_suffix_metadata.py": {
        "render_identifier",
    },
}

SUPPORT_CONTRACTS = {
    "engine/identifier/coordinator.py",
    "engine/identifier/sequence_allocator.py",
}


def _parse(relative_path: str) -> ast.Module:
    source_path = PROJECT_ROOT / relative_path
    return ast.parse(source_path.read_text(encoding="utf-8"), filename=relative_path)


def _canonical_imports(tree: ast.Module) -> list[ast.ImportFrom]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "engine.identifier_engine"
        and any(alias.name == "IdentifierEngine" for alias in node.names)
    ]


def _identifier_calls(tree: ast.Module) -> set[str]:
    methods: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {
            "generate",
            "generate_for_level",
            "render_identifier",
            "allocate_sequence",
        }:
            methods.add(node.func.attr)
    return methods


class IdentifierCallerContractTest(unittest.TestCase):
    def test_legacy_module_is_only_a_compatibility_alias(self) -> None:
        self.assertIs(LegacyIdentifierEngine, IdentifierEngine)

    def test_generators_and_runtimes_import_canonical_engine(self) -> None:
        for relative_path in (*CALLER_CONTRACTS, *SUPPORT_CONTRACTS):
            with self.subTest(path=relative_path):
                tree = _parse(relative_path)
                self.assertTrue(
                    _canonical_imports(tree),
                    f"{relative_path} must import engine.identifier_engine.IdentifierEngine",
                )

    def test_generators_and_runtimes_keep_required_call_contracts(self) -> None:
        for relative_path, expected_methods in CALLER_CONTRACTS.items():
            with self.subTest(path=relative_path):
                actual_methods = _identifier_calls(_parse(relative_path))
                self.assertTrue(
                    expected_methods.issubset(actual_methods),
                    (
                        f"{relative_path} lost IdentifierEngine calls: "
                        f"{sorted(expected_methods - actual_methods)}"
                    ),
                )

    def test_no_production_source_imports_legacy_engine(self) -> None:
        offenders: list[str] = []
        for root_name in ("engine", "common", "tools"):
            for source_path in (PROJECT_ROOT / root_name).rglob("*.py"):
                relative_path = source_path.relative_to(PROJECT_ROOT).as_posix()
                tree = ast.parse(
                    source_path.read_text(encoding="utf-8"),
                    filename=relative_path,
                )
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.ImportFrom)
                        and node.module == "core.identifier.identifier_engine"
                    ):
                        offenders.append(relative_path)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
