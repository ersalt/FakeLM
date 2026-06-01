"""Integration tests for the FastAPI endpoints."""

import json

from fastapi.testclient import TestClient


class TestModelsEndpoint:
    """Tests for GET /v1/models."""

    def test_returns_200(self, client: TestClient):
        resp = client.get("/v1/models")
        assert resp.status_code == 200

    def test_returns_valid_structure(self, client: TestClient):
        resp = client.get("/v1/models")
        data = resp.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        for model in data["data"]:
            assert "id" in model
            assert model["object"] == "model"


class TestChatCompletions:
    """Tests for POST /v1/chat/completions."""

    def test_basic_non_streaming(self, client: TestClient):
        body = {
            "model": "test",
            "messages": [
                {"role": "user", "content": "Hello, test!"},
            ],
            "max_tokens": 20,
            "stream": False,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
        assert len(data["choices"]) >= 1
        choice = data["choices"][0]
        assert "message" in choice
        assert "content" in choice["message"]
        assert len(choice["message"]["content"]) > 0

    def test_streaming(self, client: TestClient):
        body = {
            "model": "test",
            "messages": [
                {"role": "user", "content": "hi"},
            ],
            "max_tokens": 10,
            "stream": True,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200
        content = resp.text
        assert "data:" in content
        assert "[DONE]" in content

    def test_empty_messages(self, client: TestClient):
        body = {
            "model": "test",
            "messages": [],
            "max_tokens": 20,
            "stream": False,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200

    def test_intelligence_and_seed_passed(self, client: TestClient):
        body = {
            "model": "test",
            "messages": [
                {"role": "user", "content": "repeatable test"},
            ],
            "max_tokens": 10,
            "intelligence": 0.5,
            "seed": 42,
            "stream": False,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200

    def test_custom_headers(self, client: TestClient):
        body = {
            "model": "test",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
            "stream": False,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert "X-FakeLM-Engine" in resp.headers
        assert "X-FakeLM-Simulated" in resp.headers