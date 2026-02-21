import pytest
import httpx
import os
from codegen_server import app  # Your main app

@pytest.fixture(scope="session")
def test_client():
    """Live test client against running FastAPI app."""
    with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI responses for deterministic testing."""
    def mock_chat_completions(model, messages, **kwargs):
        prompt = messages[-1]["content"].lower()
        
        # Mock responses based on prompt content
        if "reverse" in prompt:
            return type("Response", (), {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": 'def reverse_string(s):return s[::-1];print(reverse_string("hello"))'})})]
            })()
        elif "count" in prompt:
            return type("Response", (), {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": 'print("strawberry".count("r"))'})})]
            })()
        elif "timeout" in prompt or "infinite" in prompt:
            return type("Response", (), {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": 'while True:pass'})})]
            })()
        elif "error" in prompt:
            return type("Response", (), {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": 'print(undefinded_variable)'})})]
            })()
        
        raise ValueError(f"No mock for prompt: {prompt}")
    
    monkeypatch.setattr("codegen_server.client.chat.completions.create", mock_chat_completions)
    monkeypatch.setattr("codegen_server.client", type("Client", (), {"chat": type("Chat", (), {"completions": type("Completions", (), {"create": mock_chat_completions})})})())
