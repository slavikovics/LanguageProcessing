import datetime as dt

from app.domain.speech import SpeechCommandDef, match_command


def _command(id: int, phrase: str, action: str, *, is_active: bool = True) -> SpeechCommandDef:
    return SpeechCommandDef(
        id=id,
        phrase=phrase,
        action=action,
        language="en",
        is_active=is_active,
        created_at=dt.datetime(2026, 1, 1),
    )


def test_match_command_finds_phrase_substring_case_insensitive():
    commands = [_command(1, "search for", "navigate_search")]
    matched = match_command("Please Search For cats", commands)
    assert matched is not None
    assert matched.action == "navigate_search"


def test_match_command_ignores_punctuation():
    commands = [_command(1, "stop reading", "stop_speaking")]
    matched = match_command("okay, stop-reading now!", commands)
    assert matched is not None
    assert matched.action == "stop_speaking"


def test_match_command_skips_inactive_commands():
    commands = [_command(1, "search for", "navigate_search", is_active=False)]
    assert match_command("search for cats", commands) is None


def test_match_command_returns_none_when_no_phrase_matches():
    commands = [_command(1, "search for", "navigate_search")]
    assert match_command("what a nice day", commands) is None


def test_match_command_returns_first_match_in_list_order():
    commands = [
        _command(1, "read this", "read_document"),
        _command(2, "read this document", "read_document_verbose"),
    ]
    matched = match_command("please read this document now", commands)
    assert matched is not None
    assert matched.id == 1
