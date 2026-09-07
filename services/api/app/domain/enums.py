from enum import Enum


class CrawlJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            CrawlJobStatus.COMPLETED,
            CrawlJobStatus.FAILED,
            CrawlJobStatus.CANCELLED,
        }


class CrawlUrlStatus(str, Enum):
    QUEUED = "queued"
    FETCHING = "fetching"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    # Never fetched at all (robots.txt disallowed it) — distinct from
    # SKIPPED, which is a page that *was* fetched and evaluated as a
    # document candidate but didn't qualify (too short, duplicate).
    BLOCKED = "blocked"


class IndexJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            IndexJobStatus.COMPLETED,
            IndexJobStatus.FAILED,
            IndexJobStatus.CANCELLED,
        }


class LangIdTrainingJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {LangIdTrainingJobStatus.COMPLETED, LangIdTrainingJobStatus.FAILED}


class LangIdRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {LangIdRunStatus.COMPLETED, LangIdRunStatus.FAILED}
