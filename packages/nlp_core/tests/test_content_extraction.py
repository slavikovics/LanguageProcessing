from nlp_core.content_extraction import extract_main_content

PAGE_WITH_CHROME = """
<html><head><title>Test</title></head><body>
<nav><ul><li><a href="/">Home</a></li><li><a href="/about">About</a></li></ul></nav>
<header><h1>Site Name</h1></header>
<aside><div class="sidebar">Related links: A, B, C</div></aside>
<article>
<h1>Article Title</h1>
<p>This is the first paragraph of the real article content, with enough text to be
picked up by the readability scoring heuristic as the main body.</p>
<p>This is a second paragraph continuing the article with more substantive content
so it clearly outweighs the nav and sidebar in scoring.</p>
</article>
<footer>Copyright 2026 Example Corp. All rights reserved.</footer>
</body></html>
"""


def test_extract_main_content_drops_navigation_header_footer_and_sidebar():
    text = extract_main_content(PAGE_WITH_CHROME)
    assert "Article Title" in text
    assert "real article content" in text
    assert "Home" not in text
    assert "Site Name" not in text
    assert "Related links" not in text
    assert "Copyright 2026" not in text


def test_extract_main_content_falls_back_on_unparseable_input():
    assert extract_main_content("") == ""


def test_extract_main_content_falls_back_when_no_article_found():
    assert extract_main_content("<html><body><p>Hello <b>world</b></p></body></html>") == "Hello world"
