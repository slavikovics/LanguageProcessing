import pytest

from app.domain.documents import DocumentError, build_document_input


def test_build_document_input_happy_path():
    doc = build_document_input(title="  Cats  ", url="  https://example.com/cats  ", clean_text="  Cats are animals.  ")
    assert doc.title == "Cats"
    assert doc.url == "https://example.com/cats"
    assert doc.clean_text == "Cats are animals."


def test_build_document_input_rejects_empty_title():
    with pytest.raises(DocumentError):
        build_document_input(title="   ", url="https://example.com", clean_text="text")


def test_build_document_input_rejects_invalid_url():
    with pytest.raises(DocumentError):
        build_document_input(title="Cats", url="not-a-url", clean_text="text")


def test_build_document_input_rejects_non_http_scheme():
    with pytest.raises(DocumentError):
        build_document_input(title="Cats", url="ftp://example.com/cats", clean_text="text")


def test_build_document_input_rejects_empty_text():
    with pytest.raises(DocumentError):
        build_document_input(title="Cats", url="https://example.com/cats", clean_text="   ")


def test_build_document_input_rejects_overlong_title():
    with pytest.raises(DocumentError):
        build_document_input(title="x" * 501, url="https://example.com", clean_text="text")
