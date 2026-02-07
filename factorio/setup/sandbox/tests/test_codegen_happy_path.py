import pytest
from httpx import AsyncClient

class TestHappyPath:
    @pytest.mark.asyncio
    async def test_reverse_string(self, test_client: AsyncClient):
        response = await test_client.post("/generate", json={
            "prompt": "Write Python function to reverse string"
        })
        data = response.json()
        
        assert response.status_code == 200
        assert data["success"] is True
        assert data["final_answer"] == "olleh"
        assert "reverse_string" in data["clean_code"]
        assert data["iterations"] == 1

    @pytest.mark.asyncio
    async def test_strawberry_count(self, test_client: AsyncClient):
        response = await test_client.post("/generate", json={
            "prompt": "How many r in strawberry"
        })
        data = response.json()
        
        assert data["final_answer"] == "3"
        assert ".count(\"r\")" in data["clean_code"]
