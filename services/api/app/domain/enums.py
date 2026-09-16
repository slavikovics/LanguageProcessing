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


class SummarizationMethod(str, Enum):
    ALGORITHMIC = "algorithmic"
    TEXTRANK = "textrank"
    EMBEDDINGS = "embeddings"


class SpeechBackend(str, Enum):
    LOCAL = "local"


class SummarizationRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {
            SummarizationRunStatus.COMPLETED,
            SummarizationRunStatus.FAILED,
            SummarizationRunStatus.CANCELLED,
        }
