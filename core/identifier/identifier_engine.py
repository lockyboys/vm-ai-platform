# import random
# import re
# from datetime import datetime
# from typing import Optional

# from core.database.database_manager import DatabaseManager


# PREFIX_PATTERN = re.compile(r"^[A-Z0-9_.-]{2,10}$")


# class IdentifierEngine:
#     """
#     SPS Identifier Engine v1.0

#     원칙:
#     - 물리 DB명을 하드코딩하지 않는다.
#     - Prefix는 COMMON DB의 공통코드에서 조회한다.
#     - Sequence는 대상 Repository DB에 저장한다.
#     - table은 database.table 형태를 고려한다.
#     - Sequence 증가는 SELECT ... FOR UPDATE로 보호한다.
#     - deleted_yn은 사용하지 않는다.
#     - change_reason은 본 테이블에 두지 않는다.
#     - 변경 사유와 상세 이력은 history 테이블에서 관리한다.
#     """

#     IDENTIFIER_TARGET_GROUP_CODE = "SPS_IDENTIFIER_TARGET"

#     COMMON_DATABASE_ROLE_CODE = "COMMON"
#     DEFAULT_SEQUENCE_DATABASE_ROLE_CODE = "STORY"

#     COMMON_CODE_TABLE_NAME = "cm_common_code"
#     IDENTIFIER_SEQUENCE_TABLE_NAME = "sp_identifier_sequence"

#     def __init__(
#         self,
#         sequence_database_role_code: str = DEFAULT_SEQUENCE_DATABASE_ROLE_CODE,
#         database_manager: Optional[DatabaseManager] = None,
#     ):
#         self.sequence_database_role_code = sequence_database_role_code.upper().strip()
#         self.database_manager = database_manager or DatabaseManager()

#     def generate_identifier(
#         self,
#         identifier_target_code: str,
#         created_by: str = "SYSTEM",
#         client_ip: Optional[str] = None,
#         program_id: str = "IdentifierEngine",
#     ) -> str:
#         target_code = self._normalize_target_code(identifier_target_code)

#         prefix = self._get_prefix_from_common_code(target_code)
#         self._validate_prefix(prefix)

#         now = datetime.now()
#         sequence_date = now.strftime("%Y%m%d")
#         time_part = now.strftime("%H%M%S")
#         random_part = f"{random.randint(0, 999):03d}"

#         sequence_no = self._increase_sequence(
#             target_code=target_code,
#             prefix=prefix,
#             sequence_date=sequence_date,
#             created_by=created_by,
#             client_ip=client_ip,
#             program_id=program_id,
#         )

#         return (
#             f"{prefix}_{sequence_date}_"
#             f"{time_part}{random_part}_"
#             f"{sequence_no:05d}"
#         )

#     def _get_prefix_from_common_code(self, target_code: str) -> str:
#         common_code_table = self.database_manager.get_qualified_table_name(
#             database_role_code=self.COMMON_DATABASE_ROLE_CODE,
#             table_name=self.COMMON_CODE_TABLE_NAME,
#         )

#         sql = f"""
#             SELECT
#                 code AS identifier_prefix
#             FROM {common_code_table}
#             WHERE group_code = %s
#               AND UPPER(code_name) = %s
#               AND status_code = 'ACTIVE'
#             LIMIT 1
#         """

#         with self.database_manager.get_connection(self.COMMON_DATABASE_ROLE_CODE) as conn:
#             with conn.cursor() as cursor:
#                 cursor.execute(sql, (self.IDENTIFIER_TARGET_GROUP_CODE, target_code))
#                 row = cursor.fetchone()

#         if not row:
#             raise ValueError(f"Identifier target code is not registered: {target_code}")

#         return row["identifier_prefix"].upper().strip()

#     def _increase_sequence(
#         self,
#         target_code: str,
#         prefix: str,
#         sequence_date: str,
#         created_by: str,
#         client_ip: Optional[str],
#         program_id: str,
#     ) -> int:
#         sequence_table = self.database_manager.get_qualified_table_name(
#             database_role_code=self.sequence_database_role_code,
#             table_name=self.IDENTIFIER_SEQUENCE_TABLE_NAME,
#         )

#         with self.database_manager.get_connection(self.sequence_database_role_code) as conn:
#             try:
#                 with conn.cursor() as cursor:
#                     select_sql = f"""
#                         SELECT
#                             identifier_sequence_id,
#                             current_sequence_no
#                         FROM {sequence_table}
#                         WHERE identifier_target_code = %s
#                           AND identifier_prefix = %s
#                           AND sequence_date = %s
#                           AND status_code = 'ACTIVE'
#                         FOR UPDATE
#                     """

#                     cursor.execute(select_sql, (target_code, prefix, sequence_date))
#                     row = cursor.fetchone()

#                     if row:
#                         next_sequence_no = int(row["current_sequence_no"]) + 1

#                         update_sql = f"""
#                             UPDATE {sequence_table}
#                             SET current_sequence_no = %s,
#                                 updated_by = %s,
#                                 updated_dt = NOW(),
#                                 client_ip = %s,
#                                 program_id = %s
#                             WHERE identifier_sequence_id = %s
#                         """

#                         cursor.execute(
#                             update_sql,
#                             (
#                                 next_sequence_no,
#                                 created_by,
#                                 client_ip,
#                                 program_id,
#                                 row["identifier_sequence_id"],
#                             ),
#                         )

#                         conn.commit()
#                         return next_sequence_no

#                     next_sequence_no = 1
#                     identifier_sequence_id = f"IS_{sequence_date}_{prefix}_{target_code}"

#                     insert_sql = f"""
#                         INSERT INTO {sequence_table} (
#                             identifier_sequence_id,
#                             identifier_target_code,
#                             identifier_prefix,
#                             sequence_date,
#                             current_sequence_no,
#                             sequence_length,
#                             status_code,
#                             created_dt,
#                             created_by,
#                             updated_dt,
#                             updated_by,
#                             client_ip,
#                             program_id
#                         )
#                         VALUES (
#                             %s, %s, %s, %s, %s,
#                             5,
#                             'ACTIVE',
#                             NOW(),
#                             %s,
#                             NOW(),
#                             %s,
#                             %s,
#                             %s
#                         )
#                     """

#                     cursor.execute(
#                         insert_sql,
#                         (
#                             identifier_sequence_id,
#                             target_code,
#                             prefix,
#                             sequence_date,
#                             next_sequence_no,
#                             created_by,
#                             created_by,
#                             client_ip,
#                             program_id,
#                         ),
#                     )

#                 conn.commit()
#                 return next_sequence_no

#             except Exception:
#                 conn.rollback()
#                 raise

#     def _normalize_target_code(self, identifier_target_code: str) -> str:
#         if not identifier_target_code:
#             raise ValueError("identifier_target_code is required.")

#         return identifier_target_code.upper().strip()

#     def _validate_prefix(self, prefix: str) -> None:
#         if not PREFIX_PATTERN.match(prefix):
#             raise ValueError(
#                 f"Invalid Identifier Prefix: {prefix}. "
#                 "Allowed pattern: ^[A-Z0-9_.-]{2,10}$"
#             )
#--------------------------------------------------------------------version: 1.0
import random
import re
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional

from core.database.database_manager import DatabaseManager


PREFIX_PATTERN = re.compile(r"^[A-Z0-9_.-]{2,10}$")


class IdentifierEngine:
    """
    SPS Identifier Engine v2.0

    기능:
    - 단건 채번
    - Batch 채번
    - Prefix Cache
    - Sequence Block Allocation
    - database.table Qualified Name 지원
    """

    IDENTIFIER_TARGET_GROUP_CODE = "SPS_IDENTIFIER_TARGET"

    COMMON_DATABASE_ROLE_CODE = "COMMON"
    DEFAULT_SEQUENCE_DATABASE_ROLE_CODE = "STORY"

    COMMON_CODE_TABLE_NAME = "cm_common_code"
    IDENTIFIER_SEQUENCE_TABLE_NAME = "sp_identifier_sequence"

    DEFAULT_BLOCK_SIZE = 100

    def __init__(
        self,
        sequence_database_role_code: str = DEFAULT_SEQUENCE_DATABASE_ROLE_CODE,
        database_manager: Optional[DatabaseManager] = None,
        block_size: int = DEFAULT_BLOCK_SIZE,
    ):
        self.sequence_database_role_code = sequence_database_role_code.upper().strip()
        self.database_manager = database_manager or DatabaseManager()
        self.block_size = self._validate_block_size(block_size)

        self._prefix_cache: Dict[str, str] = {}
        self._sequence_cache: Dict[str, deque] = defaultdict(deque)

    def load_object_blueprint(self, object_code: str) -> dict:
        """
        [Purpose]
        - Load Object Blueprint from Repository
        """

        object_table = self.database_manager.get_qualified_table_name(
            database_role_code=self.sequence_database_role_code,
            table_name="sp_object",
        )

        sql = f"""
            SELECT
                object_id,
                object_code,
                target_identifier_field,
                identifier_head_code,
                identifier_blueprint_format,
                sequence_scope_code,
                sequence_length,
                identifier_separator
            FROM {object_table}
            WHERE object_code = %s
            AND active_yn = 'Y'
            AND status_code = 'ACTIVE'
            LIMIT 1
        """

        with self.database_manager.get_connection(
            self.sequence_database_role_code
        ) as conn:

            with conn.cursor() as cursor:
                cursor.execute(sql, (object_code.upper(),))
                row = cursor.fetchone()

        if not row:
            raise ValueError(
                f"Object Blueprint not found: {object_code}"
            )

        return row

    def generate_identifier(
        self,
        identifier_target_code: str,
        created_by: str = "SYSTEM",
        client_ip: Optional[str] = None,
        program_id: str = "IdentifierEngine",
    ) -> str:
        target_code = self._normalize_target_code(identifier_target_code)
        prefix = self._get_prefix(target_code)

        sequence_date, time_part, random_part = self._get_time_parts()
        sequence_no = self._get_next_sequence_no(
            target_code=target_code,
            prefix=prefix,
            sequence_date=sequence_date,
            created_by=created_by,
            client_ip=client_ip,
            program_id=program_id,
        )

        return self._format_identifier(
            prefix=prefix,
            sequence_date=sequence_date,
            time_part=time_part,
            random_part=random_part,
            sequence_no=sequence_no,
        )

    def generate_identifiers(
        self,
        identifier_target_code: str,
        count: int,
        created_by: str = "SYSTEM",
        client_ip: Optional[str] = None,
        program_id: str = "IdentifierEngineBatch",
    ) -> List[str]:
        if count <= 0:
            raise ValueError("count must be greater than 0.")

        target_code = self._normalize_target_code(identifier_target_code)
        prefix = self._get_prefix(target_code)

        identifiers = []

        for _ in range(count):
            sequence_date, time_part, random_part = self._get_time_parts()

            sequence_no = self._get_next_sequence_no(
                target_code=target_code,
                prefix=prefix,
                sequence_date=sequence_date,
                created_by=created_by,
                client_ip=client_ip,
                program_id=program_id,
            )

            identifiers.append(
                self._format_identifier(
                    prefix=prefix,
                    sequence_date=sequence_date,
                    time_part=time_part,
                    random_part=random_part,
                    sequence_no=sequence_no,
                )
            )

        return identifiers

    def generate_identifier_map(
        self,
        request_map: Dict[str, int],
        created_by: str = "SYSTEM",
        client_ip: Optional[str] = None,
        program_id: str = "IdentifierEngineBatchMap",
    ) -> Dict[str, List[str]]:
        result = {}

        for target_code, count in request_map.items():
            result[target_code.upper().strip()] = self.generate_identifiers(
                identifier_target_code=target_code,
                count=count,
                created_by=created_by,
                client_ip=client_ip,
                program_id=program_id,
            )

        return result

    def clear_cache(self) -> None:
        self._prefix_cache.clear()
        self._sequence_cache.clear()

    def _get_prefix(self, target_code: str) -> str:
        if target_code in self._prefix_cache:
            return self._prefix_cache[target_code]

        prefix = self._get_prefix_from_common_code(target_code)
        self._validate_prefix(prefix)

        self._prefix_cache[target_code] = prefix
        return prefix

    def _get_prefix_from_common_code(self, target_code: str) -> str:
        common_code_table = self.database_manager.get_qualified_table_name(
            database_role_code=self.COMMON_DATABASE_ROLE_CODE,
            table_name=self.COMMON_CODE_TABLE_NAME,
        )

        sql = f"""
            SELECT
                code AS identifier_prefix
            FROM {common_code_table}
            WHERE group_code = %s
                AND UPPER(code_name) = %s
                AND status_code = 'ACTIVE'
            LIMIT 1
        """

        with self.database_manager.get_connection(self.COMMON_DATABASE_ROLE_CODE) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (self.IDENTIFIER_TARGET_GROUP_CODE, target_code))
                row = cursor.fetchone()

        if not row:
            raise ValueError(f"Identifier target code is not registered: {target_code}")

        return row["identifier_prefix"].upper().strip()

    def _get_next_sequence_no(
        self,
        target_code: str,
        prefix: str,
        sequence_date: str,
        created_by: str,
        client_ip: Optional[str],
        program_id: str,
    ) -> int:
        cache_key = self._get_sequence_cache_key(target_code, prefix, sequence_date)

        if not self._sequence_cache[cache_key]:
            self._allocate_sequence_block(
                target_code=target_code,
                prefix=prefix,
                sequence_date=sequence_date,
                allocation_size=self.block_size,
                created_by=created_by,
                client_ip=client_ip,
                program_id=program_id,
            )

        return self._sequence_cache[cache_key].popleft()

    def _allocate_sequence_block(
        self,
        target_code: str,
        prefix: str,
        sequence_date: str,
        allocation_size: int,
        created_by: str,
        client_ip: Optional[str],
        program_id: str,
    ) -> None:
        sequence_table = self.database_manager.get_qualified_table_name(
            database_role_code=self.sequence_database_role_code,
            table_name=self.IDENTIFIER_SEQUENCE_TABLE_NAME,
        )

        with self.database_manager.get_connection(self.sequence_database_role_code) as conn:
            try:
                with conn.cursor() as cursor:
                    select_sql = f"""
                        SELECT
                            identifier_sequence_id,
                            current_sequence_no
                        FROM {sequence_table}
                        WHERE identifier_target_code = %s
                            AND identifier_prefix = %s
                            AND sequence_date = %s
                            AND status_code = 'ACTIVE'
                        FOR UPDATE
                    """

                    cursor.execute(select_sql, (target_code, prefix, sequence_date))
                    row = cursor.fetchone()

                    if row:
                        current_no = int(row["current_sequence_no"])
                        start_no = current_no + 1
                        end_no = current_no + allocation_size

                        update_sql = f"""
                            UPDATE {sequence_table}
                            SET current_sequence_no = %s,
                                updated_by = %s,
                                updated_dt = NOW(),
                                client_ip = %s,
                                program_id = %s
                            WHERE identifier_sequence_id = %s
                        """

                        cursor.execute(
                            update_sql,
                            (
                                end_no,
                                created_by,
                                client_ip,
                                program_id,
                                row["identifier_sequence_id"],
                            ),
                        )

                    else:
                        start_no = 1
                        end_no = allocation_size
                        identifier_sequence_id = f"IS_{sequence_date}_{prefix}_{target_code}"

                        insert_sql = f"""
                            INSERT INTO {sequence_table} (
                                identifier_sequence_id,
                                identifier_target_code,
                                identifier_prefix,
                                sequence_date,
                                current_sequence_no,
                                sequence_length,
                                status_code,
                                created_dt,
                                created_by,
                                updated_dt,
                                updated_by,
                                client_ip,
                                program_id
                            )
                            VALUES (
                                %s, %s, %s, %s, %s,
                                5,
                                'ACTIVE',
                                NOW(),
                                %s,
                                NOW(),
                                %s,
                                %s,
                                %s
                            )
                        """

                        cursor.execute(
                            insert_sql,
                            (
                                identifier_sequence_id,
                                target_code,
                                prefix,
                                sequence_date,
                                end_no,
                                created_by,
                                created_by,
                                client_ip,
                                program_id,
                            ),
                        )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

        cache_key = self._get_sequence_cache_key(target_code, prefix, sequence_date)
        self._sequence_cache[cache_key].extend(range(start_no, end_no + 1))

    def _format_identifier(
        self,
        prefix: str,
        sequence_date: str,
        time_part: str,
        random_part: str,
        sequence_no: int,
    ) -> str:
        return (
            f"{prefix}_{sequence_date}_"
            f"{time_part}{random_part}_"
            f"{sequence_no:05d}"
        )

    def _get_time_parts(self):
        now = datetime.now()
        return (
            now.strftime("%Y%m%d"),
            now.strftime("%H%M%S"),
            f"{random.randint(0, 999):03d}",
        )

    def _get_sequence_cache_key(
        self,
        target_code: str,
        prefix: str,
        sequence_date: str,
    ) -> str:
        return f"{self.sequence_database_role_code}:{target_code}:{prefix}:{sequence_date}"

    def _normalize_target_code(self, identifier_target_code: str) -> str:
        if not identifier_target_code:
            raise ValueError("identifier_target_code is required.")

        return identifier_target_code.upper().strip()

    def _validate_prefix(self, prefix: str) -> None:
        if not PREFIX_PATTERN.match(prefix):
            raise ValueError(
                f"Invalid Identifier Prefix: {prefix}. "
                "Allowed pattern: ^[A-Z0-9_.-]{2,10}$"
            )

    def _validate_block_size(self, block_size: int) -> int:
        if block_size <= 0:
            raise ValueError("block_size must be greater than 0.")

        if block_size > 10000:
            raise ValueError("block_size must not exceed 10000.")

        return block_size