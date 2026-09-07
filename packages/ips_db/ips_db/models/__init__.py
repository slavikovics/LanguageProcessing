"""The one place the database schema is defined; `api` and `crawler-service`
both import these models instead of one importing the other's internals.
Status columns use plain strings (not either service's domain enums) so this
package depends on nothing but sqlalchemy.

Split by feature area, but every model shares this package's `Base` — cross-
file relationships (e.g. Collection <-> Document) resolve by class name
through SQLAlchemy's mapper registry, which is why every submodule must be
imported here before anything queries the database.
"""

from .base import MAX_EMBEDDING_DIM, Base
from .collections import Collection
from .crawl import CrawlJob, CrawlSeed, CrawlUrl
from .documents import Document, DocumentChunk, DocumentChunkEmbedding, DocumentTerm, Term, TermWeight
from .indexing import IndexJob
from .lang_id import LangIdProfile, LangIdResult, LangIdRun, LangIdRunMetric, LangIdTrainingJob
from .search import MetricResult, Query, RelevanceJudgment, SearchModel, SearchResult, SearchRun

__all__ = [
    "Base",
    "MAX_EMBEDDING_DIM",
    "Collection",
    "Document",
    "DocumentChunk",
    "DocumentChunkEmbedding",
    "Term",
    "DocumentTerm",
    "TermWeight",
    "SearchModel",
    "Query",
    "SearchRun",
    "SearchResult",
    "RelevanceJudgment",
    "MetricResult",
    "CrawlSeed",
    "CrawlJob",
    "CrawlUrl",
    "IndexJob",
    "LangIdProfile",
    "LangIdTrainingJob",
    "LangIdRun",
    "LangIdResult",
    "LangIdRunMetric",
]
