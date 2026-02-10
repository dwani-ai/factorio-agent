# Setting up Claude Code with Qwen3-Coder via llama.cpp

## Configuration

Claude Code uses MCP (Model Context Protocol) servers to connect to custom model providers. Here's how to set it up:

1. **Create/Edit your Claude Code config file:**
```bash
   mkdir -p ~/.config/claude-code
   nano ~/.config/claude-code/config.json
```

2. **Add your custom model configuration:**
```json
   {
     "mcpServers": {
       "qwen-coder": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-openai"],
         "env": {
           "OPENAI_API_KEY": "dummy-key",
           "OPENAI_BASE_URL": "https://qwen-coder.dwani.ai/v1"
         }
       }
     }
   }
```

3. **Tell Claude Code to use this model:**
   When you run `claude-code`, you can specify the model with:
```bash
   claude-code --model qwen-coder
```

   Or set it as default in your config by adding:
```json
   {
     "defaultModel": "qwen-coder",
     "mcpServers": { ... }
   }
```

## Notes:
- llama.cpp's server typically uses OpenAI-compatible API endpoints
- The "dummy-key" can be anything if your server doesn't require auth
- If your endpoint structure is different, let me know and we can adjust!

## Test it:
```bash
claude-code --model qwen-coder "write a hello world in python"
```