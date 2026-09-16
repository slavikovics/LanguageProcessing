from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SpeechCommand(Base):
    __tablename__ = "speech_commands"

    id: Mapped[int] = mapped_column(primary_key=True)
    phrase: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(50))
    language: Mapped[str] = mapped_column(String(10), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())
