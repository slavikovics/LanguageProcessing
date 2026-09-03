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
