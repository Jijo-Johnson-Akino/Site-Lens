from bs4 import BeautifulSoup

from backend.parser.structured_data import extract_json_ld


def test_valid_organization_json_ld() -> None:
    soup = BeautifulSoup(
        """<script type="application/ld+json">
        {"@type":"Organization","name":"Acme","url":"https://example.com","logo":"https://example.com/l.png"}
        </script>""",
        "html.parser",
    )
    data = extract_json_ld(soup)
    assert data["valid"] is True
    assert "Organization" in data["types"]
    assert data["entities"][0]["name"] == "Acme"


def test_invalid_json_ld() -> None:
    soup = BeautifulSoup('<script type="application/ld+json">{bad</script>', "html.parser")
    data = extract_json_ld(soup)
    assert data["valid"] is False
    assert data["parse_errors"] == 1
    assert data["script_count"] == 1


def test_graph_article_and_faq() -> None:
    soup = BeautifulSoup(
        """<script type="application/ld+json">
        {"@graph":[
          {"@type":"Article","headline":"Hello","author":{"@type":"Person","name":"Ada"}},
          {"@type":"FAQPage"}
        ]}
        </script>""",
        "html.parser",
    )
    data = extract_json_ld(soup)
    assert set(data["types"]) >= {"Article", "FAQPage", "Person"}
