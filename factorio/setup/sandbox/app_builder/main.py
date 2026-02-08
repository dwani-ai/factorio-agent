"""
App Builder UX: FastAPI + Gradio frontend for the sandbox codegen system.
Calls the codegen service /generate endpoint and displays result, code, and fix history.
"""
import os
import httpx
import gradio as gr
from fastapi import FastAPI

CODEGEN_URL = os.environ.get("CODEGEN_URL", "http://localhost:8000")
SANDBOX_LABEL = "App Builder (Codegen + Sandbox)"

app = FastAPI(
    title="App Builder",
    description="UX for prompt → generated code → sandbox execution with auto-fix",
)


async def generate_and_show(prompt: str, max_iterations: int) -> tuple[str, str, str, str]:
    """Call codegen /generate and return (answer, code, iterations, fixes) for Gradio."""
    if not (prompt or "").strip():
        return "Enter a prompt.", "", "—", "—"

    payload = {
        "prompt": prompt.strip(),
        "max_tokens": 300,
        "max_iterations": max(1, min(10, max_iterations)),
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{CODEGEN_URL}/generate", json=payload)
            r.raise_for_status()
    except httpx.ConnectError:
        return (
            "Could not reach codegen service. Is it running? (CODEGEN_URL)",
            "",
            "—",
            "—",
        )
    except httpx.HTTPStatusError as e:
        return (
            f"Codegen error: {e.response.status_code}",
            "",
            "—",
            str(e.response.text),
        )
    except Exception as e:
        return f"Error: {str(e)}", "", "—", "—"

    data = r.json()
    final_answer = data.get("final_answer", "")
    clean_code = data.get("clean_code", "")
    iterations = data.get("iterations", 0)
    fixes = data.get("fixes_applied", [])

    fixes_text = "\n".join(f"- {f}" for f in fixes) if fixes else "—"
    return final_answer, clean_code, str(iterations), fixes_text


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
            "Describe a small Python task. Code is generated, run in a sandbox, and auto-fixed on errors."
        )
        with gr.Row():
            prompt_in = gr.Textbox(
                label="Prompt",
                placeholder="e.g. Write a Python function to reverse a string",
                lines=2,
            )
        with gr.Row():
            max_iter = gr.Slider(
                minimum=1,
                maximum=10,
                value=3,
                step=1,
                label="Max auto-fix iterations",
            )
        run_btn = gr.Button("Generate & Run", variant="primary")

        with gr.Row():
            answer_out = gr.Textbox(
                label="Result (stdout)",
                lines=4,
                interactive=False,
                elem_classes=["result-box"],
            )
            code_out = gr.Code(
                label="Generated code",
                language="python",
                interactive=False,
            )
        with gr.Row():
            iter_out = gr.Textbox(label="Iterations", interactive=False)
            fixes_out = gr.Textbox(
                label="Fixes applied",
                lines=6,
                interactive=False,
                elem_classes=["result-box"],
            )

        run_btn.click(
            fn=generate_and_show,
            inputs=[prompt_in, max_iter],
            outputs=[answer_out, code_out, iter_out, fixes_out],
        )

        gr.Markdown(
            "Backend: **codegen** (LLM + auto-fix) → **sandbox** (secure execution). "
            "Set `CODEGEN_URL` if codegen runs elsewhere."
        )
    return demo


# Mount Gradio at / for the main UX; /docs for FastAPI
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
