from __future__ import annotations

import pytest
import pytest_asyncio
from ips_db import Base
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.speech import SpeechCommandService, SpeechRecognitionService, SpeechSynthesisService
from app.domain.speech import SpeechError
from app.infrastructure.speech_client import SpeechServiceError


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


class _FakeSpeechServiceClient:
    def __init__(self, *, transcript: str = "search for cats", fail: bool = False) -> None:
        self._transcript = transcript
        self._fail = fail

    async def open_synthesis_stream(self, text, *, backend, voice, rate):
        if self._fail:
            raise SpeechServiceError(422, "backend rejected the request")

        async def _chunks():
            yield b"RIFF-FAKE-HEADER"
            yield text.encode()

        return _chunks()

    async def transcribe(self, audio_bytes, *, filename, content_type, backend, language):
        if self._fail:
            raise SpeechServiceError(422, "STT backend failed")
        return {
            "transcript": self._transcript,
            "detected_language": "en",
            "backend_used": backend,
            "elapsed_ms": 12.5,
        }


@pytest.mark.asyncio
async def test_synthesis_service_streams_chunks_from_client():
    service = SpeechSynthesisService(client=_FakeSpeechServiceClient())
    stream = await service.stream("hello", backend="local", voice=None, rate=1.0)
    chunks = [chunk async for chunk in stream]
    assert chunks == [b"RIFF-FAKE-HEADER", b"hello"]


@pytest.mark.asyncio
async def test_synthesis_service_propagates_upstream_error():
    service = SpeechSynthesisService(client=_FakeSpeechServiceClient(fail=True))
    with pytest.raises(SpeechServiceError):
        await service.stream("hello", backend="local", voice=None, rate=1.0)


@pytest.mark.asyncio
async def test_recognition_service_matches_active_command(session_factory):
    async with session_factory() as session:
        commands = SpeechCommandService(session)
        await commands.create_command(phrase="search for", action="navigate_search")

        service = SpeechRecognitionService(
            session, client=_FakeSpeechServiceClient(transcript="please search for cats")
        )
        outcome, matched = await service.transcribe(
            b"fake-audio", filename="a.wav", content_type="audio/wav", backend="local", language=None
        )
        assert outcome.transcript == "please search for cats"
        assert matched is not None
        assert matched.action == "navigate_search"


@pytest.mark.asyncio
async def test_recognition_service_returns_none_when_no_command_matches(session_factory):
    async with session_factory() as session:
        commands = SpeechCommandService(session)
        await commands.create_command(phrase="search for", action="navigate_search")

        service = SpeechRecognitionService(
            session, client=_FakeSpeechServiceClient(transcript="what a nice day")
        )
        _outcome, matched = await service.transcribe(
            b"fake-audio", filename="a.wav", content_type="audio/wav", backend="local", language=None
        )
        assert matched is None


@pytest.mark.asyncio
async def test_command_service_crud(session_factory):
    async with session_factory() as session:
        service = SpeechCommandService(session)
        created = await service.create_command(phrase="stop reading", action="stop_speaking")
        assert created.is_active is True

        updated = await service.update_command(created.id, is_active=False)
        assert updated.is_active is False

        commands = await service.list_commands()
        assert len(commands) == 1

        await service.delete_command(created.id)
        assert await service.list_commands() == []


@pytest.mark.asyncio
async def test_command_service_update_unknown_command_raises(session_factory):
    async with session_factory() as session:
        service = SpeechCommandService(session)
        with pytest.raises(SpeechError):
            await service.update_command(999, is_active=False)


@pytest.mark.asyncio
async def test_command_service_delete_unknown_command_raises(session_factory):
    async with session_factory() as session:
        service = SpeechCommandService(session)
        with pytest.raises(SpeechError):
            await service.delete_command(999)
