"""호환성 모듈: 공용 MariaDB·MongoDB 쓰기 서비스는 common.database에 정의한다."""

from common.database import MariaMongoWriteService

__all__ = ["MariaMongoWriteService"]
