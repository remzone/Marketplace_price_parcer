import pytest
from priceparcer.parsers.ozon import OzonParser

@pytest.mark.asyncio
async def test_parse_ozon_search():
    parser = OzonParser()
    results = parser.parse_ozon_search("чай", scrolls=1, max_cards=1)
    parser.close()

    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert "title" in first
    assert "price_with_card" in first
    assert "url" in first
