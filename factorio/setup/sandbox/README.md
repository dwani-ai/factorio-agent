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

