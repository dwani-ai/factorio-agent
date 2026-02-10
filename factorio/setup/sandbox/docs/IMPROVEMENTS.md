# Suggested Improvements to the Sandbox / App Builder System

Prioritized by impact and effort. **P0** = high impact or bug; **P1** = strong improvement; **P2** = nice to have.

---

## P0 — Bugs & correctness

### 1. Sandbox memory limit is wrong (fixed in code)
- **Issue:** `RLIMIT_AS` uses `128 * 1024**3` → **128 GB**, not 128 MB.
- **Fix:** Use `128 * 1024**2` for 128 MB (already applied in `sandbox-server.py`).

### 2. App Builder: surface real errors ✅ implemented
- **Issue:** Codegen/sandbox failures return generic "Codegen failed" or "Sandbox error"; users can’t see timeout, 503, or stderr.
- **Improvement:** Return or display `detail` from codegen HTTP responses, and sandbox `stderr` / exit_code, so users see e.g. "Execution timeout (10s)" or "Service not ready".

---

## P1 — UX & behavior

### 3. Persist mini-apps ✅ implemented
- **Issue:** Apps live only in Gradio `State`; refresh or restart loses all apps.
- **Improvement:** Persist to a JSON file (e.g. `apps.json`) or SQLite; load on startup, save on create/delete. Optional: per-user or single global store.
- **Implementation:** JSON file at `APPS_JSON_PATH` (default: `app_builder/apps.json`); load on startup, save on create and delete.

### 4. Loading state and progress ✅ implemented
- **Issue:** "Generate & create app" and "Run this app" can take several seconds with no feedback.
- **Improvement:** Use Gradio’s progress or loading indicator; optional status text ("Generating…", "Running in sandbox…").
- **Implementation:** `gr.Progress()` in create and run handlers; "Calling codegen…", "Saving app…", "Running in sandbox…".

### 5. Show code in "My apps" and allow delete ✅ implemented
- **Issue:** User must switch to "Create" tab to see code; no way to remove an app.
- **Improvement:** When an app is selected in "My apps", show its code (read-only) and add a "Delete this app" button that removes it from state (and from persistence if added).
- **Implementation:** Read-only Code block updates on selection; "Delete this app" button removes from state and JSON.

### 6. Duplicate app names in dropdown ✅ implemented
- **Issue:** Two prompts that shorten to the same 60 chars produce the same dropdown label.
- **Improvement:** Show `name (id: xxx)` in the dropdown label, or add an optional "App name" field when creating so users can give unique names.
- **Implementation:** Dropdown choices use label `{name} (id: {id})` so every option is unique.

### 7. Optional run-time input for apps
- **Issue:** Generated apps are fixed (e.g. always reverse "hello"); no way to pass input when running.
- **Improvement:** Optional "Run with input" text area in "My apps" that gets passed as stdin to the sandbox (requires sandbox to accept stdin or a separate input param).

---

## P1 — Codegen & sandbox

### 8. Codegen: config from env
- **Improvement:** Model name, `max_tokens`, default `max_iterations`, and temperature from env (e.g. `QWEN_MODEL`, `CODEGEN_MAX_TOKENS`) so you can tune without code changes.

### 9. Sandbox: optional timeout and execution time
- **Improvement:** Allow `timeout_seconds` in execute request (cap at e.g. 30s). Return `execution_time_ms` in the response for debugging and UX.

### 10. Codegen: structured error responses
- **Improvement:** On 503/504/timeout, return a JSON body with `detail`, `retry_after` (optional), and `error_code` so the App Builder can show clear messages and optionally retry.

---

## P2 — Resilience & operations

### 11. App Builder: health checks backend
- **Improvement:** `/health` (or a separate `/ready` endpoint) optionally calls codegen and sandbox health; report "degraded" if one is down so load balancers or UI can react.

### 12. Rate limiting and cost control
- **Improvement:** Codegen: rate limit by IP or API key; optional max tokens per request or per day to avoid cost spikes. App Builder: optional per-user or global rate limit on "Create" and "Run".

### 13. Logging and observability
- **Improvement:** Structured logs (e.g. request_id, duration_ms, endpoint, status) from app-builder, codegen, and sandbox; optional OpenTelemetry or metrics (count of runs, failures, latency percentiles).

### 14. Sandbox: restrict dangerous operations
- **Improvement:** Document that isolation is process-based only. Optionally block or restrict `subprocess`, `os.system`, `socket`, `requests`, etc. via a wrapper script or a restricted interpreter (e.g. restricted execution mode or allowlist of modules).

---

## P2 — Security & auth

### 15. Optional auth for App Builder
- **Improvement:** API key or OAuth for create/run so the UI isn’t open to the whole network. FastAPI dependency for API key; Gradio can pass header or query param.

### 16. Prompt and code size limits
- **Improvement:** Codegen: max prompt length (e.g. 2000 chars); sandbox: max code length (e.g. 50 KB) to avoid abuse and accidental huge payloads.

---

## Summary table

| #  | Area        | Improvement                         | Priority |
|----|-------------|-------------------------------------|----------|
| 1  | Sandbox     | Fix memory limit 128GB → 128MB      | P0       |
| 2  | App Builder | Show real codegen/sandbox errors    | P0       |
| 3  | App Builder | Persist apps (JSON/SQLite)          | P1       |
| 4  | App Builder | Loading/progress indicators        | P1       |
| 5  | App Builder | Show code + delete in My apps       | P1       |
| 6  | App Builder | Unique dropdown labels (name + id)  | P1       |
| 7  | App Builder | Optional run-time input for apps    | P1       |
| 8  | Codegen     | Config from env                     | P1       |
| 9  | Sandbox     | Request timeout + execution_time_ms | P1       |
| 10 | Codegen     | Structured error responses          | P1       |
| 11 | App Builder | Health checks backend               | P2       |
| 12 | All         | Rate limiting / cost control        | P2       |
| 13 | All         | Structured logging / metrics        | P2       |
| 14 | Sandbox     | Document or restrict dangerous APIs | P2       |
| 15 | App Builder | Optional auth                       | P2       |
| 16 | Codegen/Sandbox | Prompt/code size limits         | P2       |
