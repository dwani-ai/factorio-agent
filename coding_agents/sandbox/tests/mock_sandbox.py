class MockSandbox:
    def __init__(self, buggy=False, timeout=False, always_fail=False):
        self.buggy = buggy
        self.timeout = timeout
        self.always_fail = always_fail
    
    async def post(self, url, json, **kwargs):
        if self.buggy:
            return MockResponse({"success": False, "stderr": "NameError: foo"})
        if self.timeout:
            return MockResponse({"success": False, "stderr": "Execution timeout"})
        if self.always_fail:
            return MockResponse({"success": False, "stderr": "Test fail"})
        return MockResponse({"success": True, "stdout": "42"})

class MockResponse:
    def __init__(self, data):
        self._json = data
    
    def json(self):
        return self._json
