from __future__ import annotations

import unittest

from tools.register_mongodb_runtime_objects import (
    load_definitions,
    reconciliation_values,
)


class _DefinitionDatabase:
    def __init__(self, rows):
        self.rows = rows

    def fetch_all(self, _sql, _parameters):
        return self.rows


class RegisterMongoDBRuntimeObjectsTest(unittest.TestCase):
    def test_load_definitions_reads_collection_master_contract(self):
        definitions = load_definitions(
            _DefinitionDatabase(
                [{
                    "code": "MCM",
                    "common_code_json": (
                        '{"object_code":"MCM","object_name":"MongoDB Collection Master",'
                        '"object_description":"Collection Master","business_code":"SP",'
                        '"domain_code":"RP","object_type_code":"REPOSITORY",'
                        '"object_level":3,"sort_no":30,'
                        '"target_identifier_field":"mongodb_document_master_id",'
                        '"identifier_target_code":"MCM",'
                        '"sequence_scope_code":"DAILY","sequence_length":5}'
                    ),
                }]
            )
        )

        self.assertEqual(definitions[0]["object_code"], "MCM")
        self.assertEqual(definitions[0]["object_name"], "MongoDB Collection Master")
        self.assertEqual(definitions[0]["object_type_code"], "REPOSITORY")
        self.assertEqual(definitions[0]["object_level"], 3)
        self.assertEqual(
            definitions[0]["target_identifier_field"],
            "mongodb_document_master_id",
        )

    def test_reconciliation_values_follow_common_repository_contract(self):
        definition = {
            "object_name": "MongoDB Collection Master",
            "object_description": "Collection Master",
            "business_code": "SP",
            "domain_code": "RP",
            "object_type_code": "REPOSITORY",
            "object_level": 3,
            "target_identifier_field": "mongodb_document_master_id",
            "identifier_target_code": "MCM",
            "sequence_scope_code": "DAILY",
            "sequence_length": 5,
        }

        self.assertEqual(
            reconciliation_values(definition),
            (
                "MongoDB Collection Master",
                "Collection Master",
                "SP",
                "RP",
                "REPOSITORY",
                3,
                "mongodb_document_master_id",
                "MCM",
                "DAILY",
                5,
            ),
        )

    def test_load_definitions_rejects_code_mismatch(self):
        with self.assertRaisesRegex(ValueError, "code mismatch"):
            load_definitions(
                _DefinitionDatabase(
                    [{
                        "code": "MCO",
                        "common_code_json": (
                            '{"object_code":"MCM","object_name":"MongoDB Collection Master",'
                            '"object_description":"Collection Master","business_code":"SP",'
                            '"domain_code":"RP","object_type_code":"REPOSITORY",'
                            '"object_level":3,"sort_no":30,'
                            '"target_identifier_field":"mongodb_document_master_id",'
                            '"identifier_target_code":"MCM",'
                            '"sequence_scope_code":"DAILY","sequence_length":5}'
                        ),
                    }]
                )
            )


if __name__ == "__main__":
    unittest.main()
