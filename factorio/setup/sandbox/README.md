Sandbox 

- Server

# Create .env
cat > .env << EOF
QWEN_API_KEY=your-key
QWEN_BASE_URL=your-endpoint
EOF

# Clean start
docker compose down -v
docker compose up --build -d

# Test
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write Python function to reverse string"}'



- Standalone


--
--

# Install
pip install pytest pytest-asyncio httpx pytest-mock

# Run all
pytest tests/ -v

# Run specific
pytest tests/test_auto_fix.py::TestAutoFixing::test_syntax_error_fix -v

# Coverage
pip install pytest-cov
pytest --cov=codegen_server --cov-report=html tests/
