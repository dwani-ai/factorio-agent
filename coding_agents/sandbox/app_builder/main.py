"""
App Builder UX: Each prompt creates an independent mini-app.
Users can create apps (prompt → codegen → stored) and run any app separately in the sandbox.
Improvements: real errors (#2), persistence (#3), progress (#4), show code + delete (#5), unique labels (#6).
"""
import json
import os
import uuid
import httpx
import gradio as gr
from fastapi import FastAPI

CODEGEN_URL = os.environ.get("CODEGEN_URL", "http://localhost:8000")
SANDBOX_URL = os.environ.get("SANDBOX_URL", "http://localhost:8001")
APPS_JSON_PATH = os.environ.get("APPS_JSON_PATH", os.path.join(os.path.dirname(__file__), "apps.json"))
SANDBOX_LABEL = "App Builder — Create & run mini-apps"

app = FastAPI(
    title="App Builder",
    description="Create mini-apps from prompts; run each app separately in the sandbox",
)


# ---- Persistence (item 3) ----

def load_apps() -> list:
    """Load mini-apps from JSON file."""
    if not os.path.isfile(APPS_JSON_PATH):
        return []
    try:
        with open(APPS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_apps(apps: list) -> None:
    """Persist mini-apps to JSON file."""
    path = APPS_JSON_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2, ensure_ascii=False)


# ---- Codegen with real errors (item 2) ----

async def generate_code(prompt: str, max_iterations: int) -> dict:
    """
    Call codegen /generate. Returns success dict or error dict.
    Success: {clean_code, final_answer, ...}; Error: {error: str, detail: str}.
    """
    payload = {
        "prompt": prompt.strip(),
        "max_tokens": 300,
        "max_iterations": max(1, min(10, max_iterations)),
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{CODEGEN_URL}/generate", json=payload)
            if r.status_code != 200:
                try:
                    body = r.json()
                    detail = body.get("detail", r.text)
                except Exception:
                    detail = r.text or f"HTTP {r.status_code}"
                return {"error": f"Codegen returned {r.status_code}", "detail": detail}
            return r.json()
    except httpx.ConnectError:
        return {"error": "Cannot reach codegen service", "detail": f"Check CODEGEN_URL (e.g. {CODEGEN_URL})"}
    except httpx.TimeoutException:
        return {"error": "Codegen timeout", "detail": "Request took longer than 60s"}
    except Exception as e:
        return {"error": "Codegen error", "detail": str(e)}


async def run_code_in_sandbox(code: str) -> tuple[str, str]:
    """Execute code in sandbox; return (stdout, stderr). Surfaces HTTP/connection errors in stderr."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{SANDBOX_URL}/execute", json={"code": code})
            if r.status_code != 200:
                try:
                    body = r.json()
                    err = body.get("stderr", body.get("detail", r.text))
                except Exception:
                    err = r.text or f"HTTP {r.status_code}"
                return "", err
            data = r.json()
            stdout = data.get("stdout", "") or "(no output)"
            stderr = data.get("stderr", "") or ""
            return stdout, stderr
    except httpx.ConnectError:
        return "", f"Cannot reach sandbox. Check SANDBOX_URL (e.g. {SANDBOX_URL})"
    except httpx.TimeoutException:
        return "", "Sandbox request timeout (15s)"
    except Exception as e:
        return "", f"Sandbox error: {str(e)}"


def _app_name(prompt: str) -> str:
    s = (prompt or "").strip()[:60]
    return s + "…" if len((prompt or "").strip()) > 60 else s


# ---- Dropdown labels: name (id: xxx) (item 6) ----

def _dropdown_choices(apps: list) -> list[tuple[str, str]]:
    """[(label, value)] for gr.Dropdown; label is unique with id."""
    return [(f"{a['name']} (id: {a['id']})", a["id"]) for a in (apps or [])]


def _find_app(apps: list, app_id: str | None) -> dict | None:
    if not app_id or not apps:
        return None
    for a in apps:
        if a.get("id") == app_id:
            return a
    return None


async def create_mini_app(
    prompt: str,
    max_iter: int,
    apps: list,
    progress: gr.Progress = gr.Progress(),
) -> tuple[list, dict, str, str]:
    """
    Generate code from prompt, add as new mini-app. Item 2: surface errors; 3: persist; 4: progress.
    Returns: (new_apps_list, dropdown_update, message, code_preview).
    """
    empty_choices = _dropdown_choices(apps)
    empty_update = gr.update(choices=empty_choices, value=None)
    if not (prompt or "").strip():
        return apps, empty_update, "Enter a prompt.", ""

    progress(0.1, desc="Calling codegen…")
    result = await generate_code(prompt, max_iter)

    if "error" in result:
        detail = result.get("detail", result["error"])
        msg = f"**Codegen failed** — {result['error']}\n\n`{detail}`"
        return apps, empty_update, msg, ""

    code = (result.get("clean_code") or "").strip()
    if not code:
        return apps, empty_update, "No code in codegen response.", ""

    progress(0.6, desc="Saving app…")
    app_id = str(uuid.uuid4())[:8]
    name = _app_name(prompt)
    new_app = {"id": app_id, "name": name, "prompt": prompt.strip(), "code": code}
    new_apps = list(apps) + [new_app]
    save_apps(new_apps)
    choices = _dropdown_choices(new_apps)
    dropdown_update = gr.update(choices=choices, value=app_id)
    progress(1.0)
    msg = f"Created mini-app: **{name}** (id: `{app_id}`). Open **My apps** to run or delete."
    return new_apps, dropdown_update, msg, code


def show_selected_app_code(app_id: str | None, apps: list) -> str:
    """Return code for selected app (item 5: show code in My apps)."""
    mini = _find_app(apps or [], app_id)
    return (mini["code"] or "") if mini else ""


def delete_app(app_id: str | None, apps: list) -> tuple[list, dict, str]:
    """Remove selected app from state and persistence (item 5). Returns (new_apps, dropdown_update, code_display)."""
    if not app_id or not apps:
        return apps or [], gr.update(choices=_dropdown_choices(apps), value=None), ""
    new_apps = [a for a in apps if a.get("id") != app_id]
    save_apps(new_apps)
    choices = _dropdown_choices(new_apps)
    new_value = new_apps[0]["id"] if new_apps else None
    return new_apps, gr.update(choices=choices, value=new_value), show_selected_app_code(new_value, new_apps)


async def run_mini_app(
    app_id: str | None,
    apps: list,
    progress: gr.Progress = gr.Progress(),
) -> tuple[str, str]:
    """Run selected mini-app in sandbox (item 4: progress)."""
    mini = _find_app(apps or [], app_id)
    if not mini:
        return "—", "Select an app to run."

    progress(0.2, desc="Running in sandbox…")
    stdout, stderr = await run_code_in_sandbox(mini["code"])
    progress(1.0)
    out_display = stdout if stdout else "(no output)"
    err_display = stderr if stderr else "—"
    return out_display, err_display


def build_ui():
    initial_apps = load_apps()

    with gr.Blocks(
        title=SANDBOX_LABEL,
        theme=gr.themes.Soft(primary_hue="slate", secondary_hue="amber"),
        css="""
        .result-box { font-family: ui-monospace, monospace; }
        """
    ) as demo:
        gr.Markdown(
            f"## {SANDBOX_LABEL}\n"
            "**Create** a mini-app from a prompt (code is generated and stored). "
            "**Run** any app separately; apps are **saved** across restarts."
        )

        apps_state = gr.State(value=initial_apps)

        with gr.Tab("Create new app"):
            gr.Markdown("Describe what you want; we generate Python code and save it as a mini-app.")
            prompt_in = gr.Textbox(
                label="Prompt",
                placeholder="e.g. Write a Python function to reverse a string",
                lines=2,
            )
            max_iter = gr.Slider(
                minimum=1, maximum=10, value=3, step=1,
                label="Max auto-fix iterations",
            )
            create_btn = gr.Button("Generate & create app", variant="primary")
            create_msg = gr.Markdown("")
            code_preview = gr.Code(label="Generated code (saved as mini-app)", language="python", interactive=False)

        with gr.Tab("My apps — Run separately"):
            gr.Markdown("Select an app, view its code, **Run** or **Delete**.")
            app_selector = gr.Dropdown(
                choices=_dropdown_choices(initial_apps),
                value=initial_apps[0]["id"] if initial_apps else None,
                label="Select mini-app",
                allow_custom_value=False,
            )
            with gr.Row():
                run_btn = gr.Button("Run this app", variant="secondary")
                delete_btn = gr.Button("Delete this app", variant="stop")
            code_display = gr.Code(
                label="Selected app code",
                language="python",
                interactive=False,
                value=show_selected_app_code(initial_apps[0]["id"] if initial_apps else None, initial_apps),
            )
            with gr.Row():
                run_stdout = gr.Textbox(
                    label="Output (stdout)",
                    lines=6,
                    interactive=False,
                    elem_classes=["result-box"],
                )
                run_stderr = gr.Textbox(
                    label="Errors (stderr)",
                    lines=4,
                    interactive=False,
                    elem_classes=["result-box"],
                )

        create_btn.click(
            fn=create_mini_app,
            inputs=[prompt_in, max_iter, apps_state],
            outputs=[apps_state, app_selector, create_msg, code_preview],
        )

        app_selector.change(
            fn=show_selected_app_code,
            inputs=[app_selector, apps_state],
            outputs=[code_display],
        )

        delete_btn.click(
            fn=delete_app,
            inputs=[app_selector, apps_state],
            outputs=[apps_state, app_selector, code_display],
        )

        run_btn.click(
            fn=run_mini_app,
            inputs=[app_selector, apps_state],
            outputs=[run_stdout, run_stderr],
        )

        gr.Markdown(
            "**Create**: codegen (LLM + auto-fix) → code stored and persisted. "
            "**Run**: sandbox executes the selected app. "
            "Apps saved to JSON; set `APPS_JSON_PATH` to change location."
        )
    return demo


demo = build_ui()
app = gr.mount_gradio_app(app, demo, path="/")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "app-builder"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7860")),
        reload=os.environ.get("RELOAD", "").lower() in ("1", "true", "yes"),
    )
