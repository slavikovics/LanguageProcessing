from app.fetcher import extract_links, extract_title

HTML = """
<html>
<head><title>  Example Page  </title></head>
<body>
  <a href="/relative">Relative</a>
  <a href="https://other.example.com/page?x=1#frag">Absolute with fragment</a>
  <a href="#top">Anchor only</a>
  <a href="javascript:void(0)">JS link</a>
  <a href="mailto:test@example.com">Mail link</a>
</body>
</html>
"""


def test_extract_links_resolves_relative_and_drops_fragments():
    links = extract_links(HTML, base_url="https://example.com/dir/")
    assert "https://example.com/relative" in links
    assert "https://other.example.com/page?x=1" in links


def test_extract_links_skips_anchors_js_and_mailto():
    links = extract_links(HTML, base_url="https://example.com/dir/")
    assert not any("javascript:" in link for link in links)
    assert not any(link.startswith("mailto:") for link in links)
    assert not any(link.endswith("#top") for link in links)


def test_extract_title_strips_whitespace():
    assert extract_title(HTML, fallback="fallback") == "Example Page"


def test_extract_title_falls_back_when_missing():
    assert extract_title("<html><body>no title</body></html>", fallback="fallback") == "fallback"
