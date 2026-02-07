class TestSandboxEdgeCases:
    @pytest.mark.asyncio
    async def test_name_error(self, test_client: AsyncClient):
        response = await test_client.post("/generate", json={
            "prompt": "Buggy code with undefined variable"
        })
        assert "NameError" in response.json()["fixes_applied"][0]

    @pytest.mark.asyncio
    async def test_empty_output(self, test_client: AsyncClient):
        response = await test_client.post("/generate", json={
            "prompt": "Write function with no print"
        })
        data = response.json()
        assert "NO_OUTPUT" in str(data["fixes_applied"])
