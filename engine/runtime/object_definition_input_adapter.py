"""
SPS Object Definition Input Adapter

Purpose:
    신규 Object Definition을 대화형으로 입력받는다.
    모든 항목에 예시와 기본값을 제공한다.
    최종 확인 단계에서 저장, 수정, 예제 보기, 종료를 지원한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUTPUT_PATH = Path("outputs/object_definition_request.json")


RELATIONSHIP_EXAMPLE: dict[str, Any] = {
    "object_code": "RELATIONSHIP",
    "object_name": "Relationship Object",
    "business_code": "SP",
    "domain_code": "RP",
    "object_type_code": "TABLE",
    "object_level": 3,
    "identifier_target_code": "RE",
    "sequence_scope_code": "DAILY",
    "sequence_length": 5,
    "object_description": (
        "Knowledge, Lifecycle, Rule, Verified SQL 등 "
        "Object 사이의 관계를 관리한다."
    ),
    "status_code": "ACTIVE",
    "active_yn": "Y",
    "version_no": "v1.0",
}


def ask_value(
    label: str,
    example: str,
    default: str,
    *,
    required: bool = True,
    uppercase: bool = False,
) -> str:
    """예시와 기본값을 표시하고 값을 입력받는다."""

    while True:
        print()
        print(label)
        print(f"예시   : {example}")
        print(f"기본값 : {default}")
        print("도움말 : ? 입력")

        value = input(f"입력 [{default}]: ").strip()

        if value == "?":
            print()
            print(f"[HELP] {label}")
            print(f"예시   : {example}")
            print(f"기본값 : {default}")
            continue

        if not value:
            value = default

        if uppercase:
            value = value.upper()

        if value or not required:
            return value

        print("[ERROR] 필수 입력값입니다.")


def ask_integer(
    label: str,
    example: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """정수 값을 입력받고 범위를 검증한다."""

    while True:
        raw_value = ask_value(
            label=label,
            example=example,
            default=str(default),
        )

        try:
            value = int(raw_value)
        except ValueError:
            print("[ERROR] 숫자로 입력해야 합니다.")
            continue

        if minimum <= value <= maximum:
            return value

        print(
            f"[ERROR] {minimum} 이상 {maximum} 이하로 입력해야 합니다."
        )


def collect_object_definition() -> dict[str, Any]:
    """신규 Object Definition Request를 입력받는다."""

    print("=" * 70)
    print("SPS Object Definition Input")
    print("=" * 70)
    print("Enter를 누르면 표시된 기본값이 사용됩니다.")
    print("?를 입력하면 해당 항목의 예제를 다시 볼 수 있습니다.")

    object_code = ask_value(
        label="Object Code",
        example="RELATIONSHIP, RULE, API, SCREEN",
        default="RELATIONSHIP",
        uppercase=True,
    )

    object_name = ask_value(
        label="Object Name",
        example="Relationship Object",
        default="Relationship Object",
    )

    business_code = ask_value(
        label="Business Code",
        example="SP = Story Programming, HC = Health Companion",
        default="SP",
        uppercase=True,
    )

    domain_code = ask_value(
        label="Domain Code",
        example="RP = Repository, EN = Engine, GN = Generator",
        default="RP",
        uppercase=True,
    )

    object_type_code = ask_value(
        label="Object Type Code",
        example="TABLE, REPOSITORY, DATABASE, COLUMN, API, ENGINE",
        default="TABLE",
        uppercase=True,
    )

    object_level = ask_integer(
        label="Object Level",
        example=(
            "0 Framework / 1 Repository / 2 Database "
            "/ 3 Table / 4 Column"
        ),
        default=3,
        minimum=0,
        maximum=4,
    )

    identifier_target_code = ask_value(
        label="Identifier Target Code",
        example="RE = Relationship, SQ = SQL, AP = API, OB = Object",
        default="RE",
        uppercase=True,
    )

    sequence_scope_code = ask_value(
        label="Sequence Scope Code",
        example="NO, YEARLY, MONTHLY, DAILY",
        default="DAILY",
        uppercase=True,
    )

    sequence_length = ask_integer(
        label="Sequence Length",
        example="5 = 00001",
        default=5,
        minimum=1,
        maximum=20,
    )

    object_description = ask_value(
        label="Object Description",
        example=(
            "Knowledge, Lifecycle, Rule, Verified SQL 등 "
            "Object 사이의 관계를 관리한다."
        ),
        default=RELATIONSHIP_EXAMPLE["object_description"],
    )

    return {
        "object_code": object_code,
        "object_name": object_name,
        "business_code": business_code,
        "domain_code": domain_code,
        "object_type_code": object_type_code,
        "object_level": object_level,
        "identifier_target_code": identifier_target_code,
        "sequence_scope_code": sequence_scope_code,
        "sequence_length": sequence_length,
        "object_description": object_description,
        "status_code": "ACTIVE",
        "active_yn": "Y",
        "version_no": "v1.0",
    }


def show_example() -> None:
    """RELATIONSHIP Object 등록 예제를 출력한다."""

    print()
    print("=" * 70)
    print("RELATIONSHIP Object 등록 예제")
    print("=" * 70)

    for key, value in RELATIONSHIP_EXAMPLE.items():
        print(f"{key:<28}: {value}")

    print("=" * 70)


def show_summary(request: dict[str, Any]) -> None:
    """현재 입력값과 주요 예제를 함께 출력한다."""

    level_names = {
        0: "Framework",
        1: "Repository",
        2: "Database",
        3: "Table",
        4: "Column",
    }

    print()
    print("=" * 70)
    print("Object Definition Summary")
    print("=" * 70)

    print(f"Object Code             : {request['object_code']}")
    print("  예시                  : RELATIONSHIP / RULE / API / SCREEN")

    print(f"Object Name             : {request['object_name']}")
    print("  예시                  : Relationship Object")

    print(f"Business Code           : {request['business_code']}")
    print("  예시                  : SP = Story Programming")

    print(f"Domain Code             : {request['domain_code']}")
    print("  예시                  : RP = Repository")

    print(f"Object Type Code        : {request['object_type_code']}")
    print("  예시                  : TABLE / DATABASE / COLUMN / API")

    print(
        f"Object Level            : {request['object_level']} "
        f"({level_names.get(request['object_level'], 'Unknown')})"
    )
    print("  예시                  : 0 / 1 / 2 / 3 / 4")

    print(
        f"Identifier Target Code  : "
        f"{request['identifier_target_code']}"
    )
    print("  예시                  : RE = Relationship")

    print(
        f"Sequence Scope Code     : "
        f"{request['sequence_scope_code']}"
    )
    print("  예시                  : DAILY / MONTHLY / YEARLY / NO")

    print(f"Sequence Length         : {request['sequence_length']}")
    print("  예시                  : 5 = 00001")

    print(f"Object Description      : {request['object_description']}")

    print("=" * 70)


def select_modify_field(request: dict[str, Any]) -> dict[str, Any]:
    """사용자가 선택한 단일 항목을 수정한다."""

    fields = {
        "1": "object_code",
        "2": "object_name",
        "3": "business_code",
        "4": "domain_code",
        "5": "object_type_code",
        "6": "object_level",
        "7": "identifier_target_code",
        "8": "sequence_scope_code",
        "9": "sequence_length",
        "10": "object_description",
    }

    print()
    print("수정할 항목")
    print("1. Object Code")
    print("2. Object Name")
    print("3. Business Code")
    print("4. Domain Code")
    print("5. Object Type Code")
    print("6. Object Level")
    print("7. Identifier Target Code")
    print("8. Sequence Scope Code")
    print("9. Sequence Length")
    print("10. Object Description")
    print("Q. 수정 취소")

    choice = input("선택: ").strip().upper()

    if choice == "Q":
        return request

    field = fields.get(choice)

    if field is None:
        print("[ERROR] 올바른 항목을 선택하세요.")
        return request

    current_value = request[field]

    if field == "object_level":
        request[field] = ask_integer(
            label="Object Level",
            example="0 / 1 / 2 / 3 / 4",
            default=int(current_value),
            minimum=0,
            maximum=4,
        )

    elif field == "sequence_length":
        request[field] = ask_integer(
            label="Sequence Length",
            example="5 = 00001",
            default=int(current_value),
            minimum=1,
            maximum=20,
        )

    else:
        uppercase_fields = {
            "object_code",
            "business_code",
            "domain_code",
            "object_type_code",
            "identifier_target_code",
            "sequence_scope_code",
        }

        request[field] = ask_value(
            label=field,
            example=str(RELATIONSHIP_EXAMPLE.get(field, current_value)),
            default=str(current_value),
            uppercase=field in uppercase_fields,
        )

    return request


def confirm_request(
    request: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """최종 저장 여부를 입력받는다."""

    while True:
        show_summary(request)

        print()
        print("[Y] 저장")
        print("[E] 전체 예제 보기")
        print("[M] 입력값 수정")
        print("[N] 처음부터 다시 입력")
        print("[Q] 종료")

        choice = input("선택 [Y/E/M/N/Q]: ").strip().upper()

        if choice == "Y":
            return "SAVE", request

        if choice == "E":
            show_example()
            continue

        if choice == "M":
            request = select_modify_field(request)
            continue

        if choice == "N":
            return "RESTART", request

        if choice == "Q":
            return "QUIT", request

        print("[ERROR] Y, E, M, N, Q 중 하나를 입력하세요.")


def save_request(request: dict[str, Any]) -> Path:
    """입력 Request를 JSON으로 저장한다."""

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return OUTPUT_PATH


def main() -> int:
    while True:
        request = collect_object_definition()
        action, request = confirm_request(request)

        if action == "RESTART":
            print("[INFO] 처음부터 다시 입력합니다.")
            continue

        if action == "QUIT":
            print("[CANCEL] Object Definition 입력을 종료했습니다.")
            return 0

        output_path = save_request(request)

        print()
        print("=" * 70)
        print("[OK] Object Definition Request 저장 완료")
        print(f"Output : {output_path}")
        print("=" * 70)

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
