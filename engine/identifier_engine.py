# engine/identifier_engine.py

from datetime import datetime
import random


class IdentifierEngine:
    def __init__(self, database_manager):
        self.database_manager = database_manager
        self.object_cache = {}

    def load_object_blueprint(self, object_code: str) -> dict:
        if object_code in self.object_cache:
            return self.object_cache[object_code]

        sql = """
        SELECT
            object_id,
            object_code,
            target_identifier_field,
            identifier_head_code,
            identifier_blueprint_format,
            sequence_scope_code,
            sequence_length,
            identifier_separator
        FROM te_story_platform.sp_object
        WHERE object_code = %s
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
        """

        row = self.database_manager.fetch_one(sql, (object_code,))

        if not row:
            raise ValueError(f"Object Blueprint not found: {object_code}")

        self.object_cache[object_code] = row
        return row

    def generate(self, object_code: str) -> str:
        blueprint = self.load_object_blueprint(object_code)

        head = blueprint["identifier_head_code"]
        fmt = blueprint["identifier_blueprint_format"]
        seq_len = int(blueprint["sequence_length"])
        sep = blueprint["identifier_separator"] or "_"

        now = datetime.now()
        sequence_no = self.allocate_sequence(object_code, blueprint["sequence_scope_code"])

        values = {
            "HEAD": head,
            "YYYY": now.strftime("%Y"),
            "YYYYMM": now.strftime("%Y%m"),
            "YYYYMMDD": now.strftime("%Y%m%d"),
            "HHMMSS": now.strftime("%H%M%S"),
            "HHMMSSMS": now.strftime("%H%M%S") + f"{int(now.microsecond / 1000):03d}",
            "RANDOM3": f"{random.randint(0, 999):03d}",
            "SEQ5": str(sequence_no).zfill(seq_len),
        }

        identifier = fmt

        for key, value in values.items():
            identifier = identifier.replace("{" + key + "}", value)

        return identifier.replace("__", sep)

    def allocate_sequence(self, object_code: str, sequence_scope_code: str) -> int:
        # 기존 Sequence Block Allocation 로직 연결
        # 지금은 임시 형태
        return self.database_manager.next_sequence(
            sequence_key=object_code,
            sequence_scope_code=sequence_scope_code,
        )