from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LangIdProfile(Base):

    __tablename__ = "lang_id_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    method: Mapped[str] = mapped_column(String(20))
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    profile_data: Mapped[dict] = mapped_column(JSON)
    source_document_count: Mapped[int] = mapped_column(Integer, default=0)
    source_char_count: Mapped[int] = mapped_column(Integer, default=0)
    built_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("method", "language", name="uq_lang_id_profile_method_language"),
    )


class LangIdTrainingJob(Base):

    __tablename__ = "lang_id_training_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    epochs_total: Mapped[int] = mapped_column(Integer, default=0)
    epochs_completed: Mapped[int] = mapped_column(Integer, default=0)
    current_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_train_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class LangIdRun(Base):

    __tablename__ = "lang_id_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    documents_total: Mapped[int] = mapped_column(Integer, default=0)
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)


class LangIdResult(Base):

    __tablename__ = "lang_id_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("lang_id_runs.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    predicted_language: Mapped[str] = mapped_column(String(10))
    distances: Mapped[dict] = mapped_column(JSON)
    elapsed_ms: Mapped[float] = mapped_column(Float)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "document_id", name="uq_lang_id_result_run_document"),
    )


class LangIdRunMetric(Base):

    __tablename__ = "lang_id_run_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("lang_id_runs.id", ondelete="CASCADE"))
    metric_name: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Float)
