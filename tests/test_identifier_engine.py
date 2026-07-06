# import re

# from core.identifier.identifier_engine import IdentifierEngine


# IDENTIFIER_PATTERN = re.compile(
#     r"^[A-Z0-9_.-]{2,10}_[0-9]{8}_[0-9]{9}_[0-9]{5}$"
# )


# def main():
#     engine = IdentifierEngine(sequence_database_role_code="STORY")

#     targets = [
#         "BUSINESS",
#         "DOMAIN",
#         "OBJECT",
#         "ENTITY",
#         "ATTRIBUTE",
#         "RELATIONSHIP",
#         "METADATA",
#         "SQL",
#         "DOCUMENT",
#         "API",
#         "GENERATOR",
#         "ENGINE",
#     ]

#     generated_identifiers = []

#     for target in targets:
#         identifier = engine.generate_identifier(
#             identifier_target_code=target,
#             created_by="SYSTEM",
#             program_id="test_identifier_engine.py",
#         )

#         if not IDENTIFIER_PATTERN.match(identifier):
#             raise AssertionError(f"Invalid identifier format: {identifier}")

#         generated_identifiers.append(identifier)
#         print(f"{target:<12} => {identifier}")

#     if len(generated_identifiers) != len(set(generated_identifiers)):
#         raise AssertionError("Duplicated identifier generated.")

#     print("\nIdentifier Engine test completed successfully.")


# if __name__ == "__main__":
#     main()
#--------------------------------------------------------------------version: 0.5

# import re
# from collections import Counter

# from core.identifier.identifier_engine import IdentifierEngine


# IDENTIFIER_PATTERN = re.compile(
#     r"^[A-Z0-9_.-]{2,10}_[0-9]{8}_[0-9]{9}_[0-9]{5}$"
# )


# def validate_identifiers(identifiers):
#     if not identifiers:
#         raise AssertionError("No identifiers generated.")

#     for identifier in identifiers:
#         if not IDENTIFIER_PATTERN.match(identifier):
#             raise AssertionError(f"Invalid identifier format: {identifier}")

#     duplicated = [
#         identifier
#         for identifier, count in Counter(identifiers).items()
#         if count > 1
#     ]

#     if duplicated:
#         raise AssertionError(f"Duplicated identifiers generated: {duplicated}")


# def main():
#     engine = IdentifierEngine(
#         sequence_database_role_code="STORY",
#         block_size=50,
#     )

#     print("Single Mode Test")
#     single_targets = [
#         "BUSINESS",
#         "DOMAIN",
#         "OBJECT",
#         "ENTITY",
#         "ATTRIBUTE",
#         "RELATIONSHIP",
#         "METADATA",
#         "SQL",
#         "DOCUMENT",
#         "API",
#         "GENERATOR",
#         "ENGINE",
#     ]

#     single_identifiers = []

#     for target in single_targets:
#         identifier = engine.generate_identifier(
#             identifier_target_code=target,
#             created_by="SYSTEM",
#             program_id="test_identifier_engine_single.py",
#         )
#         single_identifiers.append(identifier)
#         print(f"{target:<12} => {identifier}")

#     validate_identifiers(single_identifiers)

#     print("\nBatch Mode Test")
#     batch_identifiers = engine.generate_identifiers(
#         identifier_target_code="OBJECT",
#         count=120,
#         created_by="SYSTEM",
#         program_id="test_identifier_engine_batch.py",
#     )

#     validate_identifiers(batch_identifiers)

#     print(f"OBJECT batch count => {len(batch_identifiers)}")
#     print(f"OBJECT batch first => {batch_identifiers[0]}")
#     print(f"OBJECT batch last  => {batch_identifiers[-1]}")

#     print("\nBatch Map Test")
#     identifier_map = engine.generate_identifier_map(
#         request_map={
#             "BUSINESS": 3,
#             "DOMAIN": 3,
#             "ENTITY": 5,
#             "ATTRIBUTE": 5,
#             "SQL": 3,
#         },
#         created_by="SYSTEM",
#         program_id="test_identifier_engine_batch_map.py",
#     )

#     all_map_identifiers = []

#     for target, identifiers in identifier_map.items():
#         validate_identifiers(identifiers)
#         all_map_identifiers.extend(identifiers)
#         print(f"{target:<12} => {len(identifiers)} generated")

#     validate_identifiers(all_map_identifiers)

#     print("\nIdentifier Engine v2.0 test completed successfully.")


# if __name__ == "__main__":
#     main()
#--------------------------------------------------------------------version: 0.8
# tests/test_identifier_engine.py

# def test_object_identifier_generation(identifier_engine):
#     identifier = identifier_engine.generate("OBJECT")

#     print("OBJECT generated =>", identifier)

#     blueprint = identifier_engine.load_object_blueprint("OBJECT")

#     print("OBJECT blueprint")
#     print("object_id                 =>", blueprint["object_id"])
#     print("object_code               =>", blueprint["object_code"])
#     print("target_identifier_field   =>", blueprint["target_identifier_field"])
#     print("identifier_head_code      =>", blueprint["identifier_head_code"])
#     print("identifier_blueprint      =>", blueprint["identifier_blueprint_format"])
#     print("sequence_scope_code       =>", blueprint["sequence_scope_code"])
#     print("sequence_length           =>", blueprint["sequence_length"])
#     print("identifier_separator      =>", blueprint["identifier_separator"])

#     assert identifier.startswith("OB_")
#     assert blueprint["target_identifier_field"] == "object_id"

# if __name__ == "__main__":
#     print("=" * 60)
#     print("Story Programming Identifier Engine Test Start")
#     print("=" * 60)

#     # 실제 파일 안에 있는 테스트 함수명으로 교체
#     test_object_identifier_generation()

#     print("=" * 60)
#     print("Story Programming Identifier Engine Test End")
#     print("=" * 60)
#--------------------------------------------------------------------version: 0.9
# tests/test_identifier_engine.py
"""
SPS Object First Identifier Engine Test

[Purpose]
- Test Identifier Engine with Object First structure
- Load Object Blueprint from sp_object
- Generate Object Identifier
- Print Repository / Blueprint / Identifier result

[Rule]
- Test is also Object
- Human and Machine Readable
- No silent test
"""

from core.identifier.identifier_engine import IdentifierEngine


class TestIdentifierEngineRunner:
    """
    [Purpose]
    - Run Identifier Engine test without pytest fixture

    [Role]
    - Create IdentifierEngine
    - Load Object Blueprint
    - Generate Identifier
    - Print verification result
    """

    def __init__(self):
        self.identifier_engine = IdentifierEngine(
            sequence_database_role_code="STORY"
        )

    def run(self):
        print("=" * 60)
        print("Story Programming Identifier Engine Test Start")
        print("=" * 60)

        self.test_object_identifier_generation()

        print("=" * 60)
        print("Story Programming Identifier Engine Test End")
        print("=" * 60)

    def test_object_identifier_generation(self):
        object_code = "OBJECT"

        blueprint = self.identifier_engine.load_object_blueprint(object_code)
        identifier = self.identifier_engine.generate_identifier(object_code)

        print()
        print("[Generated Identifier]")
        print("OBJECT generated =>", identifier)

        print()
        print("[Object Blueprint]")
        print("object_id                 =>", blueprint["object_id"])
        print("object_code               =>", blueprint["object_code"])
        print("target_identifier_field   =>", blueprint["target_identifier_field"])
        print("identifier_head_code      =>", blueprint["identifier_head_code"])
        print("identifier_blueprint      =>", blueprint["identifier_blueprint_format"])
        print("sequence_scope_code       =>", blueprint["sequence_scope_code"])
        print("sequence_length           =>", blueprint["sequence_length"])
        print("identifier_separator      =>", blueprint["identifier_separator"])

        expected_head = blueprint["identifier_head_code"]

        assert identifier.startswith(expected_head + "_")
        assert blueprint["target_identifier_field"] == "object_id"

        print()
        print("[Result]")
        print("PASS")


def test_object_identifier_generation(identifier_engine):
    """
    [Purpose]
    - Pytest compatible test function
    """
    identifier = identifier_engine.generate_identifier("OBJECT")
    blueprint = identifier_engine.load_object_blueprint("OBJECT")

    assert identifier.startswith(blueprint["identifier_head_code"] + "_")
    assert blueprint["target_identifier_field"] == "object_id"


def main():
    runner = TestIdentifierEngineRunner()
    runner.run()


if __name__ == "__main__":
    main()