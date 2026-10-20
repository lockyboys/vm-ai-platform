"""네트워크/LLM 없이 임시 파일로 자동 수정·복구 계약을 검증한다."""
import ast
import fcntl
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "sample.py"
        self.original = b"def answer():\n    return 1\n"
        self.target.write_bytes(self.original)
        # 시험 저장소에만 기준 커밋을 만든다. 운영 프로젝트의 Git은 변경하지 않는다.
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "sample.py"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Repair Test",
                        "-c", "user.email=repair-test@example.invalid", "commit", "-qm", "baseline"], check=True)
        settings = types.ModuleType("config")
        settings.BASE_DIR = self.root
        settings.SPS_SOURCE_REPAIR_ALLOWED_PATHS = ("sample.py",)
        settings.SPS_SOURCE_REPAIR_MAX_BYTES = 100000
        settings.SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS = 3
        settings.SPS_SOURCE_REPAIR_AUDIT_DIR = "audit"
        common = types.ModuleType("common.common_function")
        def normalize(value, label):
            text = str(value or "").strip()
            if not text:
                raise ValueError(label)
            return text
        common.normalize_required_text = normalize
        spec = importlib.util.spec_from_file_location("repair_under_test", ROOT / "haness/source_repair.py")
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"config": settings, "common.common_function": common}):
            spec.loader.exec_module(self.module)
        self.test = '''import runpy, unittest
class Regression(unittest.TestCase):
    def test_answer(self):
        self.assertEqual(runpy.run_path(SOURCE_PATH)["answer"](), 2)
'''

    def repair(self, **kwargs):
        request = dict(file_path="sample.py", old_code="return 1", new_code="return 2",
                       regression_test=self.test,
                       expected_sha256=hashlib.sha256(self.original).hexdigest(), dry_run=True)
        request.update(kwargs)
        return self.module.repair_source(**request)

    def test_dry_run_preserves_original_and_tests_candidate(self):
        result = self.repair()
        self.assertTrue(result["success"])
        self.assertFalse(result["applied"])
        self.assertFalse(result["baseline"]["passed"])
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(list(self.root.glob("*BACKUP*")))

    def test_apply_preserves_backup_and_audit(self):
        result = self.repair(dry_run=False)
        self.assertTrue(result["applied"])
        self.assertEqual((self.root / result["backup"]).read_bytes(), self.original)
        self.assertEqual(self.target.read_text(), self.original.decode().replace("return 1", "return 2"))
        record = json.loads(next((self.root / "audit").glob("*.json")).read_text())
        self.assertEqual(record["state"], "APPLIED")

    def test_invalid_paths_and_policy_files(self):
        for value in ("../sample.py", str(self.target), "config.py", "haness/source_repair.py", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.repair(file_path=value)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_symlink_escape_rejected(self):
        self.target.unlink()
        self.target.symlink_to(ROOT / "haness/source_repair.py")
        with self.assertRaises(ValueError):
            self.repair()

    def test_stale_hash_rejected(self):
        with self.assertRaises(ValueError):
            self.repair(expected_sha256="0" * 64)

    def test_uncommitted_source_is_blocked_before_patch(self):
        self.target.write_bytes(self.original + b"# uncommitted\n")
        before = self.target.read_bytes()
        with self.assertRaises(self.module.PreCommitRequired):
            self.repair(expected_sha256=hashlib.sha256(before).hexdigest(), dry_run=False)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(list(self.root.glob("*BACKUP*")))

    def test_staged_change_is_blocked(self):
        self.target.write_bytes(self.original + b"# staged\n")
        subprocess.run(["git", "-C", str(self.root), "add", "sample.py"], check=True)
        self.target.write_bytes(self.original)
        with self.assertRaises(self.module.PreCommitRequired):
            self.repair()

    def test_source_read_reports_commit_requirement(self):
        self.target.write_bytes(self.original + b"# uncommitted\n")
        result = self.module.read_repair_source("sample.py")
        self.assertEqual(result["git_checkpoint"]["error_code"], "PRE_COMMIT_REQUIRED")

    def test_invalid_or_ambiguous_patch_rejected(self):
        for change in ({"old_code": ""}, {"old_code": "absent"}, {"new_code": "return 1"},
                       {"new_code": "return ("}, {"dry_run": "false"}):
            with self.subTest(change=change), self.assertRaises((ValueError, SyntaxError)):
                self.repair(**change)

    def test_missing_and_already_passing_tests_rejected(self):
        for source in ("import unittest", self.test.replace(", 2)", ", 1)")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.repair(regression_test=source)

    def test_failed_candidate_is_not_applied(self):
        result = self.repair(new_code="return 3", dry_run=False)
        self.assertFalse(result["success"])
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_timeout_fails_without_applying(self):
        with patch.object(self.module.subprocess, "run", side_effect=subprocess.TimeoutExpired("test", 3)):
            with self.assertRaises(ValueError):
                self.repair(dry_run=False)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_graph_ends_after_applied_patch(self):
        tree = ast.parse((ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py").read_text())
        node = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "after_tools")
        namespace = {"json": json, "END": "END", "AgentState": dict}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "route", "exec"), namespace)
        message = types.SimpleNamespace(type="tool", name="source_patch", content='{"applied":true}')
        self.assertEqual(namespace["after_tools"]({"messages": [message]}), "END")
        message.content = '{"applied":false}'
        self.assertEqual(namespace["after_tools"]({"messages": [message]}), "agent")

    def test_post_failure_rolls_back(self):
        real_check = self.module._check
        def fail_after_apply(candidate, test_file, dry_run):
            if candidate == self.target:
                return {"passed": False, "tests": 1}
            return real_check(candidate, test_file, dry_run)
        with patch.object(self.module, "_check", side_effect=fail_after_apply):
            with self.assertRaises(RuntimeError):
                self.repair(dry_run=False)
        self.assertEqual(self.target.read_bytes(), self.original)
        record = json.loads(next((self.root / "audit").glob("*.json")).read_text())
        self.assertEqual(record["state"], "ROLLED_BACK")

    def test_concurrent_change_is_preserved(self):
        real_check = self.module._check
        def changed_source(candidate, test_file, dry_run):
            result = real_check(candidate, test_file, dry_run)
            self.target.write_text("# another editor\n")
            return result
        with patch.object(self.module, "_check", side_effect=changed_source):
            with self.assertRaises(ValueError):
                self.repair(dry_run=False)
        self.assertEqual(self.target.read_text(), "# another editor\n")

    def test_langgraph_tool_uses_guarded_repair(self):
        tree = ast.parse((ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py").read_text())
        functions = {node.name: node for node in ast.walk(tree)
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        source = ast.unparse(functions["source_patch"])
        self.assertIn("repair_source", source)
        self.assertNotIn("git", source)
        self.assertNotIn("open(", source)
        self.assertIn("read_repair_source", functions)
        self.assertIn("ToolNode", ast.unparse(tree))
        self.assertIn("StateGraph", ast.unparse(tree))


if __name__ == "__main__":
    unittest.main(verbosity=2)
