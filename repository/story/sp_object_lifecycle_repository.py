import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


class SpObjectLifecycleRepository:
    def __init__(self):
        env_path = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(dotenv_path=env_path)

        self.connection = pymysql.connect(
            host=os.getenv("STORY_PLATFORM_MARIADB_HOST", os.getenv("COMMON_MARIADB_HOST")),
            port=int(os.getenv("STORY_PLATFORM_MARIADB_PORT", os.getenv("COMMON_MARIADB_PORT", "3306"))),
            user=os.getenv("STORY_PLATFORM_MARIADB_USER", os.getenv("COMMON_MARIADB_USER")),
            password=os.getenv("STORY_PLATFORM_MARIADB_PASSWORD", os.getenv("COMMON_MARIADB_PASSWORD")),
            database=os.getenv("STORY_PLATFORM_MARIADB_DATABASE", "te_story_platform"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    def close_current_lifecycle(self, object_id):
        sql = """
            UPDATE sp_object_lifecycle
               SET current_yn = 'N',
                   effective_end_dt = NOW(),
                   updated_by = 'SYSTEM',
                   updated_dt = NOW()
             WHERE object_id = %s
               AND current_yn = 'Y'
               AND deleted_yn = 'N'
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql, (object_id,))

    def change_status(self, object_id, status_code, event_code=None, reason=None, note=None):
        if event_code is None:
            event_code = f"{status_code}_EVENT"

        return self.create_lifecycle(
            object_id=object_id,
            lifecycle_status_code=status_code,
            lifecycle_event_code=event_code,
            lifecycle_reason=reason,
            lifecycle_note=note,
        )

    def created(self, object_id, reason=None, note=None):
        return self.change_status(
            object_id=object_id,
            status_code="CREATED",
            event_code="OBJECT_CREATED",
            reason=reason,
            note=note,
        )

    def registered(self, object_id, reason=None, note=None):
        return self.change_status(
            object_id=object_id,
            status_code="REGISTERED",
            event_code="OBJECT_REGISTERED",
            reason=reason,
            note=note,
        )

    def active(self, object_id, reason=None, note=None):
        return self.change_status(
            object_id=object_id,
            status_code="ACTIVE",
            event_code="OBJECT_ACTIVATED",
            reason=reason,
            note=note,
        )

    def disposed(self, object_id, reason=None, note=None):
        return self.change_status(
            object_id=object_id,
            status_code="DISPOSED",
            event_code="OBJECT_DISPOSED",
            reason=reason,
            note=note,
        )

    def create_lifecycle(
        self,
        object_id,
        lifecycle_status_code,
        lifecycle_event_code,
        lifecycle_reason=None,
        lifecycle_note=None,
    ):
        self.close_current_lifecycle(object_id)

        sql = """
            INSERT INTO sp_object_lifecycle (
                object_id,
                lifecycle_status_code,
                lifecycle_event_code,
                lifecycle_reason,
                lifecycle_note,
                created_by,
                program_id
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                'SYSTEM',
                'sp_object_lifecycle_repository'
            )
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    object_id,
                    lifecycle_status_code,
                    lifecycle_event_code,
                    lifecycle_reason,
                    lifecycle_note,
                ),
            )
            lifecycle_id = cursor.lastrowid

        self.connection.commit()
        return lifecycle_id

    def get_current_lifecycle(self, object_id):
        sql = """
            SELECT *
              FROM sp_object_lifecycle
             WHERE object_id = %s
               AND current_yn = 'Y'
               AND deleted_yn = 'N'
             ORDER BY object_lifecycle_id DESC
             LIMIT 1
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql, (object_id,))
            return cursor.fetchone()


if __name__ == "__main__":
    repo = SpObjectLifecycleRepository()

    lifecycle_id = repo.created(
        object_id=1,
        reason="초기 테스트",
        note="SPS Object Lifecycle 단순 create 테스트",
    )

    print("created lifecycle_id =", lifecycle_id)
    print(repo.get_current_lifecycle(1))

