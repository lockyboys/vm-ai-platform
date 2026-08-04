import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.register_object_level_classification_rule_action import (
    build_action_value,
    build_explicit_action_value,
)


class ObjectLevelClassificationRuleActionTest(unittest.TestCase):
    def test_default_action_contract_uses_issued_verified_query_id(self):
        contract = json.loads(
            build_action_value(
                verified_query_id="issued-query-id",
                condition_id="issued-negative-condition-id",
            )
        )

        self.assertEqual("issued-query-id", contract["verified_query_id"])
        self.assertEqual("ACTION_TYPE", contract["action_type_group_code"])
        self.assertEqual("issued-negative-condition-id", contract["condition_id"])
        self.assertEqual(
            {"rule_resolution_source": "DEFAULT"},
            contract["condition_context"],
        )
        self.assertEqual(4, contract["default_object_level"])
        self.assertEqual(["DEFAULT"], contract["resolution_order"])

    def test_explicit_action_contract_binds_one_condition(self):
        contract = json.loads(
            build_explicit_action_value(
                condition_id="issued-condition-id",
                object_level=3,
            )
        )

        self.assertEqual("issued-condition-id", contract["condition_id"])
        self.assertEqual(3, contract["object_level"])
        self.assertEqual(["EXPLICIT_RULE"], contract["resolution_order"])
        self.assertNotIn("default_object_level", contract)

    def test_standalone_script_registers_project_root_before_imports(self):
        project_root = Path(__file__).resolve().parents[2]
        script_path = (
            project_root / "tools" / "register_object_level_classification_rule_action.py"
        )
        command = "\n".join(
            [
                "import runpy",
                "import sys",
                f"project_root = {str(project_root)!r}",
                "sys.path[:] = ["
                "entry for entry in sys.path "
                "if entry not in ('', project_root)"
                "]",
                f"runpy.run_path({str(script_path)!r}, run_name='standalone_import_check')",
            ]
        )
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)

        with tempfile.TemporaryDirectory() as working_directory:
            result = subprocess.run(
                [sys.executable, "-c", command],
                cwd=working_directory,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
