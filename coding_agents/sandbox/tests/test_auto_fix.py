import pytest
from httpx import AsyncClient

class TestAutoFixing:
    @pytest.mark.asyncio
    async def test_syntax_error_fix(self, test_client: AsyncClient, monkeypatch):
        # Mock initial buggy response
        monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: MockSandbox(buggy=True))
        
        response = await test_client.post("/generate", json={
            "prompt": "Write function counting vowels",
            "max_iterations": 2
        })
        data = response.json()
        
        assert data["iterations"] == 2  # Fixed on retry
        assert data["final_answer"] != "Max iterations reached"

    @pytest.mark.asyncio
    async def test_timeout_fix(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: MockSandbox(timeout=True))
        
        response = await test_client.post("/generate", json={
            "prompt": "Write infinite loop (will timeout)"
        })
        data = response.json()
        
        assert "timeout" in data["fixes_applied"][0]
        assert data["iterations"] <= 3

    @pytest.mark.asyncio
    async def test_max_iterations(self, test_client: AsyncClient, monkeypatch):
        monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: MockSandbox(always_fail=True))
        
        response = await test_client.post("/generate", json={
            "prompt": "Always failing test",
            "max_iterations": 2
        })
        data = response.json()
        
        assert data["iterations"] == 2
        assert data["final_answer"] == "Max iterations reached"
