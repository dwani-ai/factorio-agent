"""
App Builder UX: Each prompt creates an independent mini-app.
Users can create apps (prompt → codegen → stored) and run any app separately in the sandbox.
"""
import os
import uuid
import httpx
import gradio as gr
from fastapi import FastAPI

CODEGEN_URL = os.environ.get("CODEGEN_URL", "http://localhost:8000")
SANDBOX_URL = os.environ.get("SANDBOX_URL", "http://localhost:8001")
SANDBOX_LABEL = "App Builder — Create & run mini-apps"

app = FastAPI(
    title="App Builder",
    description="Create mini-apps from prompts; run each app separately in the sandbox",
)


async def generate_code(prompt: str, max_iterations: int) -> dict | None:
    """Call codegen /generate; return parsed result or None on error."""
    payload = {
        "prompt": prompt.strip(),
        "max_tokens": 300,
        "max_iterations": max(1, min(10, max_iterations)),
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{CODEGEN_URL}/generate", json=payload)
            r.raise_for_status()
        return r.json()
    except Exception:
        return None


async def run_code_in_sandbox(code: str) -> tuple[str, str]:
    """Execute code in sandbox; return (stdout, stderr)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{SANDBOX_URL}/execute", json={"code": code})
            r.raise_for_status()
        data = r.json()
        return (
            data.get("stdout", "") or "(no output)",
            data.get("stderr", "") or "",
        )
    except Exception as e:
        return "", f"Sandbox error: {str(e)}"


def _app_name(prompt: str) -> str:
    s = (prompt or "").strip()[:60]
    return s + "…" if len((prompt or "").strip()) > 60 else s


async def create_mini_app(prompt: str, max_iter: int, apps: list) -> tuple[list, dict, str, str]:
    """
    Generate code from prompt, add as new mini-app.
    Returns: (new_apps_list, dropdown_update, message, code_preview).
    """
    empty_choices = _dropdown_choices(apps)
    empty_update = gr.update(choices=empty_choices, value=None)
    if not (prompt or "").strip():
        return apps, empty_update, "Enter a prompt.", ""

    result = await generate_code(prompt, max_iter)
    if not result:
        return apps, empty_update, "Codegen failed (check CODEGEN_URL).", ""

    code = result.get("clean_code", "").strip()
    if not code:
        return apps, empty_update, "No code generated.", ""

    app_id = str(uuid.uuid4())[:8]
    name = _app_name(prompt)
    new_app = {"id": app_id, "name": name, "prompt": prompt.strip(), "code": code}
    new_apps = list(apps) + [new_app]
    choices = _dropdown_choices(new_apps)
    dropdown_update = gr.update(choices=choices, value=app_id)
    msg = f"Created mini-app: **{name}** (id: `{app_id}`). Open **My apps** and click **Run this app** to execute."
    return new_apps, dropdown_update, msg, code


def _dropdown_choices(apps: list) -> list[tuple[str, str]]:
    """[(label, value)] for gr.Dropdown."""
    return [(a["name"], a["id"]) for a in (apps or [])]


def _find_app(apps: list, app_id: str | None) -> dict | None:
    if not app_id or not apps:
        return None
    for a in apps:
        if a.get("id") == app_id:
            return a
    return None


async def run_mini_app(app_id: str | None, apps: list) -> tuple[str, str]:
    """Run selected mini-app in sandbox; return (stdout_display, stderr_display)."""
    mini = _find_app(apps or [], app_id)
    if not mini:
        return "—", "Select an app to run."
    stdout, stderr = await run_code_in_sandbox(mini["code"])
    out_display = stdout if stdout else "(no output)"
    err_display = stderr if stderr else "—"
    return out_display, err_display


def build_ui():
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
            "**Run** any app separately in the sandbox."
        )

        apps_state = gr.State(value=[])

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
            gr.Markdown("Select an app and click **Run** to execute it in the sandbox.")
            app_selector = gr.Dropdown(
                choices=[],
                label="Select mini-app to run",
                allow_custom_value=False,
            )
            run_btn = gr.Button("Run this app", variant="secondary")
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
        run_btn.click(
            fn=run_mini_app,
            inputs=[app_selector, apps_state],
            outputs=[run_stdout, run_stderr],
        )

        gr.Markdown(
            "**Create**: codegen (LLM + auto-fix) → code stored as mini-app. "
            "**Run**: sandbox executes the selected app's code. "
            "Set `CODEGEN_URL` and `SANDBOX_URL` if services run elsewhere."
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