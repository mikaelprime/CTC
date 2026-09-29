"""Panel web de consulta: la página se sirve y los datos que pide exigen
sesión (la página en sí no expone nada)."""

from tests.conftest import client


def test_panel_page_is_served():
    response = client.get("/panel")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Panel de consulta" in response.text


def test_panel_data_requires_login():
    for path in ("/cashier/daily", "/reports/upcoming-payments?days=7", "/audit/"):
        assert client.get(path).status_code == 401
