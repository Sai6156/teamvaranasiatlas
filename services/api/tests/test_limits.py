import pytest
from atlas import extraction


def test_repeated_csv_headers_cannot_expand_without_bound(monkeypatch):
    monkeypatch.setattr(extraction, "MAX_TEXT", 1000)
    data = "wide_" + "x" * 500 + ",value\n" + "\n".join("a,b" for _ in range(45))
    with pytest.raises(ValueError, match="processing limit"):
        extraction.extract(data.encode(), "wide.csv")
