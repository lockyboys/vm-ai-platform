from __future__ import annotations

import unittest

from tools.register_ui_repository_objects import load_definitions


class _DefinitionDatabase:
    def __init__(self, rows):
        self.rows = rows

    def fetch_all(self, _sql, _parameters):
        return self.rows


class RegisterUiRepositoryObjectsTest(unittest.TestCase):
    def test_load_definitions_reads_active_metadata_contract(self):
        definitions = load_definitions(
            _DefinitionDatabase(
                [{
                    "code": "SP_UI_SCREEN",
                    "common_code_json": (
                        '{"object_code":"SP_UI_SCREEN","object_name":"UI Screen",'
                        '"object_description":"Screen","business_code":"SP",'
                        '"domain_code":"RP","object_type_code":"TABLE",'
                        '"object_level":3,"sort_no":10,'
                        '"target_identifier_field":"object_id",'
                        '"identifier_target_code":"OB",'
                        '"sequence_scope_code":"YEARLY","sequence_length":5}'
                    ),
                }]
            )
        )
        self.assertEqual(definitions[0]["object_code"], "SP_UI_SCREEN")
        self.assertEqual(definitions[0]["object_level"], 3)
        self.assertEqual(definitions[0]["identifier_target_code"], "OB")

    def test_load_definitions_rejects_code_mismatch(self):
        with self.assertRaisesRegex(ValueError, "code mismatch"):
            load_definitions(
                _DefinitionDatabase(
                    [{
                        "code": "SP_UI_MENU",
                        "common_code_json": (
                            '{"object_code":"SP_UI_SCREEN","object_name":"UI Screen",'
                            '"object_description":"Screen","business_code":"SP",'
                            '"domain_code":"RP","object_type_code":"TABLE",'
                            '"object_level":3,"sort_no":10,'
                            '"target_identifier_field":"object_id",'
                            '"identifier_target_code":"OB",'
                            '"sequence_scope_code":"YEARLY","sequence_length":5}'
                        ),
                    }]
                )
            )


if __name__ == "__main__":
    unittest.main()
