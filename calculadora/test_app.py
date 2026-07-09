import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Calculadora" in resp.data


def test_sum_get(client):
    resp = client.get("/sum?a=5&b=3")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 8.0


def test_sum_post(client):
    resp = client.post("/sum", json={"a": 10, "b": 4})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 14.0


def test_subtract_get(client):
    resp = client.get("/subtract?a=5&b=3")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 2.0


def test_subtract_negative_result(client):
    resp = client.get("/subtract?a=3&b=5")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == -2.0


def test_missing_params(client):
    resp = client.get("/sum?a=5")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_invalid_params(client):
    resp = client.get("/sum?a=foo&b=3")
    assert resp.status_code == 400
    assert "error" in resp.get_json()

def test_multiply_get(client):
    resp = client.get("/multiply?a=5&b=3")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 15.0


def test_multiply_post(client):
    resp = client.post("/multiply", json={"a": 4, "b": 6})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 24.0

def test_mod_get(client):
    resp = client.get("/mod?a=10&b=3")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 1.0


def test_mod_post(client):
    resp = client.post("/mod", json={"a": 9, "b": 4})
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 1.0

def test_divide_by_zero(client):
    response = client.get("/divide?a=1&b=0")
    assert response.status_code == 400
    
def test_mod_by_zero(client):
    resp = client.get("/mod?a=5&b=0")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
