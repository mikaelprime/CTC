from tests.conftest import client

def test_docs():
    response = client.get("/docs")

    assert response.status_code == 200