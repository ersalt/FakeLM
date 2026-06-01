"""End-to-end integration tests for FakeLM."""

import json

from fastapi.testclient import TestClient


class TestFullWorkflow:
    """Tests that verify the full request lifecycle."""

    def test_models_then_chat(self, client: TestClient):
        """Verify models listing then chaining to a chat request."""
        # 1. List models
        resp = client.get("/v1/models")
        assert resp.status_code == 200
        models = resp.json()["data"]
        model_id = models[0]["id"]

        # 2. Send a chat request using the first reported model
        body = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Tell me something interesting."}],
            "max_tokens": 50,
            "temperature": 0.7,
            "seed": 123,
            "stream": False,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == model_id
        assert len(data["choices"][0]["message"]["content"]) > 0

    def test_streaming_full_flow(self, client: TestClient):
        """Test streaming request produces valid SSE events and concludes with [DONE]."""
        body = {
            "model": "fake-gpt-4",
            "messages": [{"role": "user", "content": "stream test"}],
            "max_tokens": 25,
            "stream": True,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200
        content = resp.text
        lines = [line for line in content.split("\n") if line]
        data_lines = [l for l in lines if l.startswith("data:")]
        assert len(data_lines) >= 1
        assert "data: [DONE]" in lines[-1] if lines else False

    def test_invalid_max_tokens(self, client: TestClient):
        """Test with max_tokens=0 — should be caught by pydantic validation."""
        body = {
            "model": "test",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 0,
        }
        resp = client.post("/v1/chat/completions", json=body)
        # Pydantic validation during InternalRequest construction should return 422
        assert resp.status_code == 422

    def test_no_messages_field(self, client: TestClient):
        """Test with no messages field — should still work (empty prompt)."""
        body = {
            "model": "test",
            "max_tokens": 10,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200

    def test_system_message_alone(self, client: TestClient):
        """Test with only system message — should produce output."""
        body = {
            "model": "test",
            "messages": [{"role": "system", "content": "You are a helpful assistant."}],
            "max_tokens": 20,
        }
        resp = client.post("/v1/chat/completions", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["choices"][0]["message"]["content"]) > 0