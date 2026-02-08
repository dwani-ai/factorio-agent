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

# Test API
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write Python function to reverse string"}'

- App Builder UX (FastAPI + Gradio)

With the stack running, open the App Builder UI:

  http://localhost:7860

The app-builder service calls the codegen API; set `CODEGEN_URL` if codegen runs elsewhere. To run the UX only (codegen on host):

  cd app_builder && pip install -r requirements.txt && CODEGEN_URL=http://localhost:8000 uvicorn main:app --host 0.0.0.0 --port 7860

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
