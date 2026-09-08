from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .crawl import CrawlJob
    from .documents import Document


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    documents_changed_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="collection", passive_deletes=True
    )
    crawl_jobs: Mapped[list["CrawlJob"]] = relationship(
        back_populates="collection", passive_deletes=True
    )
