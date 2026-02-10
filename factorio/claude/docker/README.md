docker build -t claude-code .
docker run -it -v $(pwd):/app \
  -e ANTHROPIC_BASE_URL=http://host.docker.internal:8080/v1 \
  -e ANTHROPIC_AUTH_TOKEN=dummy \
  claude-code
