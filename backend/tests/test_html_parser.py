from backend.parser.html_parser import parse_html

SAMPLE = """
<!doctype html>
<html lang="en-US">
  <head>
    <title> Example Website </title>
    <meta name="description" content="Example description">
    <link rel="canonical" href="https://example.com/">
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <h1>Hello</h1>
    <h2>One</h2>
    <h2>Two</h2>
    <a href="/about">About</a>
    <a href="https://example.com/blog">Blog</a>
    <img src="/logo.png" alt="">
    <form action="/go"></form>
    <script src="/app.js"></script>
  </body>
</html>
"""


def test_extracts_core_fields() -> None:
    data = parse_html(SAMPLE)
    assert data["title"] == "Example Website"
    assert data["meta_description"] == "Example description"
    assert data["canonical"] == "https://example.com/"
    assert data["language"] == "en"
    assert data["h1_count"] == 1
    assert data["h2_count"] == 2
    assert data["link_count"] == 2
    assert data["image_count"] == 1
    assert data["script_count"] == 1
    assert data["stylesheet_count"] == 1
    assert data["form_count"] == 1
    assert data["title_present"] is True
    assert data["h1s"][0]["text"] == "Hello"
    assert data["images"][0]["empty_alt"] is True
    assert data["links"][0]["rel"] is None


def test_anchor_rel_is_captured() -> None:
    data = parse_html('<a href="/about" rel="nofollow noopener">About</a>')
    assert data["links"][0]["rel"] == "nofollow noopener"
