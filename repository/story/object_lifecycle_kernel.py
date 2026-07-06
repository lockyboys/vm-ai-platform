class ObjectLifecycleKernel:
    CREATED = "CREATED"
    REGISTERED = "REGISTERED"
    SCANNED = "SCANNED"
    PARSED = "PARSED"
    CLASSIFIED = "CLASSIFIED"
    ANALYZED = "ANALYZED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    REVISED = "REVISED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"
    DISPOSAL_REQUESTED = "DISPOSAL_REQUESTED"
    DISPOSED = "DISPOSED"

    @staticmethod
    def make_lifecycle_uid(year: int, sequence_no: int) -> str:
        return f"OL_{year}_{sequence_no:05d}"
