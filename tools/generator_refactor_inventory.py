from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGET_FILES = (
    "engine/generator/repository_generator.py",
    "engine/generator/repository_execution_plan_builder.py",
    "engine/generator/object_definition_generator.py",
    "engine/generator/relationship_generator.py",
    "engine/generator/metadata_generator.py",
)

OUTPUT_DIR = PROJECT_ROOT / "result" / "generator_refactor"
JSON_PATH = OUTPUT_DIR / "generator_refactor_inventory.json"
TEXT_PATH = OUTPUT_DIR / "generator_refactor_inventory.txt"


@dataclass
class FunctionInfo:
    name: str
    line_no: int
    arguments: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ClassInfo:
    name: str
    line_no: int
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ModuleInfo:
    path: str
    exists: bool
    line_count: int = 0
    imports: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    syntax_error: str | None = None
    references: list[str] = field(default_factory=list)


def node_name(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> FunctionInfo:
    arguments: list[str] = []

    all_args = (
        list(node.args.posonlyargs)
        + list(node.args.args)
        + list(node.args.kwonlyargs)
    )

    for arg in all_args:
        arguments.append(arg.arg)

    if node.args.vararg is not None:
        arguments.append(f"*{node.args.vararg.arg}")

    if node.args.kwarg is not None:
        arguments.append(f"**{node.args.kwarg.arg}")

    return FunctionInfo(
        name=node.name,
        line_no=node.lineno,
        arguments=arguments,
        decorators=[
            node_name(decorator)
            for decorator in node.decorator_list
        ],
        is_async=isinstance(node, ast.AsyncFunctionDef),
    )


def find_references(module_path: Path) -> list[str]:
    module_name = module_path.stem

    command = [
        "grep",
        "-RIn",
        "--exclude-dir=.git",
        "--exclude-dir=venv",
        "--exclude-dir=__pycache__",
        "--exclude=*.pyc",
        module_name,
        str(PROJECT_ROOT),
    ]

    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    references: list[str] = []

    for line in process.stdout.splitlines():
        if str(module_path) in line:
            continue

        references.append(line)

    return references[:200]


def inspect_module(relative_path: str) -> ModuleInfo:
    module_path = PROJECT_ROOT / relative_path

    if not module_path.exists():
        return ModuleInfo(
            path=relative_path,
            exists=False,
        )

    source = module_path.read_text(encoding="utf-8")

    module_info = ModuleInfo(
        path=relative_path,
        exists=True,
        line_count=len(source.splitlines()),
    )

    try:
        tree = ast.parse(source, filename=str(module_path))
    except SyntaxError as exc:
        module_info.syntax_error = (
            f"{exc.msg} at line {exc.lineno}, column {exc.offset}"
        )
        return module_info

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_info.imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            imported_names = ", ".join(
                alias.name
                for alias in node.names
            )

            module_info.imports.append(
                f"from {node.module or ''} import {imported_names}"
            )

        elif isinstance(node, ast.ClassDef):
            class_info = ClassInfo(
                name=node.name,
                line_no=node.lineno,
                bases=[
                    node_name(base)
                    for base in node.bases
                ],
            )

            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    class_info.methods.append(
                        function_info(child)
                    )

            module_info.classes.append(class_info)

        elif isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            module_info.functions.append(
                function_info(node)
            )

    module_info.references = find_references(module_path)

    return module_info


def render_text(modules: list[ModuleInfo]) -> str:
    lines: list[str] = []

    lines.append("=" * 78)
    lines.append("SPS Generator Integration Refactoring Inventory")
    lines.append("=" * 78)

    for module in modules:
        lines.append("")
        lines.append("-" * 78)
        lines.append(f"MODULE : {module.path}")
        lines.append("-" * 78)
        lines.append(f"EXISTS     : {module.exists}")
        lines.append(f"LINE COUNT : {module.line_count}")

        if module.syntax_error:
            lines.append(f"SYNTAX ERROR : {module.syntax_error}")
            continue

        lines.append("")
        lines.append("[IMPORTS]")

        if module.imports:
            for item in module.imports:
                lines.append(f"- {item}")
        else:
            lines.append("- NONE")

        lines.append("")
        lines.append("[CLASSES]")

        if module.classes:
            for class_info in module.classes:
                base_text = ", ".join(class_info.bases) or "object"

                lines.append(
                    f"- {class_info.name}"
                    f" (line={class_info.line_no}, bases={base_text})"
                )

                for method in class_info.methods:
                    arguments = ", ".join(method.arguments)

                    lines.append(
                        f"    · {method.name}({arguments})"
                        f" line={method.line_no}"
                    )
        else:
            lines.append("- NONE")

        lines.append("")
        lines.append("[MODULE FUNCTIONS]")

        if module.functions:
            for function in module.functions:
                arguments = ", ".join(function.arguments)

                lines.append(
                    f"- {function.name}({arguments})"
                    f" line={function.line_no}"
                )
        else:
            lines.append("- NONE")

        lines.append("")
        lines.append("[REFERENCES]")

        if module.references:
            lines.extend(
                f"- {reference}"
                for reference in module.references
            )
        else:
            lines.append("- NONE")

    lines.append("")
    lines.append("=" * 78)
    lines.append("END")
    lines.append("=" * 78)

    return "\n".join(lines)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    modules = [
        inspect_module(relative_path)
        for relative_path in TARGET_FILES
    ]

    JSON_PATH.write_text(
        json.dumps(
            [asdict(module) for module in modules],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    text_result = render_text(modules)

    TEXT_PATH.write_text(
        text_result,
        encoding="utf-8",
    )

    print(text_result)
    print("")
    print(f"JSON RESULT : {JSON_PATH.relative_to(PROJECT_ROOT)}")
    print(f"TEXT RESULT : {TEXT_PATH.relative_to(PROJECT_ROOT)}")

    failed = [
        module.path
        for module in modules
        if not module.exists or module.syntax_error
    ]

    if failed:
        print("")
        print("STATUS : ERROR")
        print("FAILED MODULES:")
        for path in failed:
            print(f"- {path}")
        return 1

    print("")
    print("STATUS : OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
