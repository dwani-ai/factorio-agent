Agent Harness Instruction

- LLM API Server [Setup](llm_api/README.md) 

- Sandbox Server [Setup](sandbox/README.md)


Architecture Diagram

```ascii
┌─────────────┐       POST /generate       ┌─────────────────┐
│    Client   │ ──────────────────────────▶│ Codegen Service │
│ (curl/UI)   │                            │   (FastAPI)     │
└─────────────┘                            │                 │
                                            │  • Qwen3-Coder  │
                                            │  • Code clean   │
                                            │  • HTTP → SB    │
                                            └─────────────────┘
                                                       │
                                                       ▼ POST /execute
                                            ┌─────────────────┐
                                            │ Sandbox Service │
                                            │   (FastAPI)     │
                                            │                 │
                                            │  • Subprocess   │
                                            │  • CPU/mem lim  │
                                            └─────────────────┘
                                                       ▲
                                            │ stdout/stderr
                                            └─────────────────┘

```

---

Data flow diagram


```ascii
                    Data Flow: "How many r in strawberry?"

┌─────────────────┐  1. POST /generate     ┌──────────────────┐
│     Client      │ ─────────────────────▶ │ Codegen Service  │
│                 │                        │ (FastAPI)        │
│ curl / Web UI   │                        │                  │
└─────────────────┘                        │ ┌──────────────┐ │
                                           │ │ 2. Qwen3-Coder│ │
                                           │ │ via OpenAI    │ │
                                           │ └──────────────┘ │
                                           │ ┌──────────────┐ │
                                           │ │ 3. Code Clean │ │
                                           │ │ (strip fences │ │
                                           │ │   # comments) │ │
                                           │ └──────────────┘ │
                                           │ ┌──────────────┐ │
                                           │ │ 4. POST       │ │
                                           │ │ /execute      │ │
                                           │ │ { code }      │ │
                                           │ └──────────────┘ │
                                                      │
                                                      ▼ 5. POST /execute { code }
                                           ┌──────────────────┐
                                           │ Sandbox Service  │
                                           │ (FastAPI)        │
                                           │ ┌──────────────┐ │
                                           │ │ 6. Subprocess │ │
                                           │ │ python -c code│ │
                                           │ └──────────────┘ │
                                           │ ┌──────────────┐ │
                                           │ │ 7. Resource   │ │
                                           │ │ Limits        │ │
                                           │ │ CPU:2s Mem:128│ │
                                           │ └──────────────┘ │
                                           └──────────────────┘
                                                      │
                                                      ▼ 8. Return { stdout, stderr }
                                                      │
                                           ┌──────────────────┐
                                           │ Codegen Service  │
                                           │ ┌──────────────┐ │
                                           │ │ Aggregate     │ │
                                           │ │ Response      │ │
                                           │ └──────────────┘ │
                                           └──────────────────┘
                                                      │
                                                      ▼ 9. JSON { final_answer, code, logs }
                                                      │
                                           ┌──────────────────┐
                                           │     Client       │
                                           │ ┌──────────────┐ │
                                           │ │ "There are 3  │ │
                                           │ │ 'r' in        │ │
                                           │ │ 'strawberry'" │ │
                                           │ └──────────────┘ │
                                           └──────────────────┘

```
