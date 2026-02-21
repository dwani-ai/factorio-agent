from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import re
import httpx
import uvicorn
from openai import OpenAI
from contextlib import asynccontextmanager
import json


client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = OpenAI(api_key=os.environ["QWEN_API_KEY"], base_url=os.environ["QWEN_BASE_URL"])
    yield
    client = None


app = FastAPI(title="Auto‑fixing Codegen API", lifespan=lifespan)
SANDBOX_SERVICE_URL = os.environ.get("SANDBOX_URL", "http://sandbox:8001")


class CodeRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 200
    max_iterations: Optional[int] = 3


class AutoFixResult(BaseModel):
    final_answer: str
    iterations: int
    clean_code: str
    raw_response: str
    fixes_applied: list[str]


def needs_fix(sandbox_response: dict) -> tuple[bool, str]:
    """Analyze sandbox response and decide if fix needed."""
    if sandbox_response.get("success") and sandbox_response["stdout"].strip():
        return False, "Success"
    
    stderr = sandbox_response.get("stderr", "")
    if "timeout" in stderr.lower():
        return True, "TIMEOUT"
    if "SyntaxError" in stderr:
        return True, "SYNTAX_ERROR"
    if "NameError" in stderr:
        return True, "NAME_ERROR"
    if "TypeError" in stderr:
        return True, "TYPE_ERROR"
    if "no output" in sandbox_response.get("stdout", "").lower():
        return True, "NO_OUTPUT"
    
    return False, "OTHER_ERROR"

async def auto_fix_loop(prompt: str, max_iterations: int = 3) -> AutoFixResult:
    """Main auto‑fix loop."""
    history = []
    current_prompt = prompt
    
    for iteration in range(max_iterations):
        # Step 1: Generate code
        response = client.chat.completions.create(
            model="qwen3-coder",
            messages=[
                {"role": "system", "content": """You are a Python code generator. RULES:
- Output ONLY valid Python code that runs immediately when pasted into Python interpreter
- NO ``` markdown fences, NO # comments, NO explanations  
- Include function definition + test call + print(result)
EVERY response MUST be directly executable Python ONLY."""},
                {"role": "user", "content": current_prompt}
            ],
            max_tokens=300,
            temperature=0.3 if iteration > 0 else 0.7  # Lower temp on retries
        )
        
        content = response.choices[0].message.content.strip()
        clean_code = re.sub(r'```(?:python)?|```', '', content).strip()
        clean_code = re.sub(r'#.*?(?=\n|$)', '', clean_code, flags=re.MULTILINE).strip()
        
        # Step 2: Execute in sandbox
        async with httpx.AsyncClient(timeout=45.0) as http_client:
            sandbox_resp = await http_client.post(f"{SANDBOX_SERVICE_URL}/execute", json={"code": clean_code})
            sandbox_data = sandbox_resp.json()
        
        history.append({
            "iteration": iteration + 1,
            "code": clean_code,
            "sandbox": sandbox_data
        })
        
        # Step 3: Check if fix needed
        needs_fix_flag, error_type = needs_fix(sandbox_data)
        if not needs_fix_flag:
            return AutoFixResult(
                final_answer=sandbox_data["stdout"].strip(),
                iterations=iteration + 1,
                clean_code=clean_code,
                raw_response=content,
                fixes_applied=[f"Iteration {i+1}: Success" for i in range(iteration + 1)]
            )
        
        # Step 4: Generate fix prompt
        fix_prompt = f"""Previous code failed with error: {sandbox_data['stderr']}

Original task: {prompt}

Fix this code to work correctly:
{clean_code}

ERROR TYPE: {error_type}
"""
        current_prompt = fix_prompt
        print(f"🔄 Iteration {iteration + 1}: {error_type}")
    
    # Max iterations reached
    return AutoFixResult(
        final_answer="Max iterations reached",
        iterations=max_iterations,
        clean_code=clean_code,
        raw_response=content,
        fixes_applied=[h["sandbox"]["stderr"] for h in history]
    )

class ProjectDesignRequest(BaseModel):
    """High-level request to generate a multi-file project."""

    prompt: str
    max_files: int = 20
    max_tokens_per_file: int = 800
    temperature: float = 0.4


class GeneratedFile(BaseModel):
    path: str
    code: str


class ProjectGenerationResult(BaseModel):
    """Result of multi-step project generation."""

    files: list[GeneratedFile]
    design_json: str
    errors: list[str]


async def _call_llm(messages: list[dict], max_tokens: int = 512, temperature: float = 0.4) -> str:
    """Small helper to call the Qwen chat model and return content."""
    global client
    if client is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    resp = client.chat.completions.create(
        model="qwen3-coder",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


async def design_project(request: ProjectDesignRequest) -> dict:
    """
    Step 1: Ask the model to design the project and return JSON describing files.

    This avoids stuffing the full program into a single 32K-context call.
    """
    system_msg = {
        "role": "system",
        "content": (
            "You are a senior software architect. Your job is to DESIGN a Python project, "
            "not to write all code at once.\n\n"
            "Respond ONLY with minified JSON, no markdown and no comments. Schema:\n"
            "{\n"
            '  \"summary\": \"short project summary\",\n'
            '  \"files\": [\n'
            "    {\n"
            '      \"path\": \"relative/path.py\",\n'
            '      \"description\": \"what goes in this file\",\n'
            '      \"functions\": [\"fn1\", \"fn2\", \"...\"]\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Keep `files` length <= {max_files}.\n"
        ),
    }
    user_msg = {
        "role": "user",
        "content": request.prompt,
    }
    raw = await _call_llm(
        [system_msg, user_msg],
        max_tokens=1024,
        temperature=request.temperature,
    )

    # Strip fences if any
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail=f"Model returned invalid JSON for project design: {cleaned[:400]}",
        )

    files = data.get("files") or []
    if len(files) > request.max_files:
        data["files"] = files[: request.max_files]
    return data


async def generate_file_code(
    project_prompt: str,
    design: dict,
    file_spec: dict,
    max_tokens: int,
    temperature: float,
) -> str:
    """
    Step 2: For a single file, generate ONLY that file's content.

    We pass in a compact project summary + this file's description, so each
    call stays well below the 32K context limit.
    """
    summary = design.get("summary", "")
    path = file_spec.get("path", "app.py")
    description = file_spec.get("description", "")
    functions = file_spec.get("functions", [])

    system_msg = {
        "role": "system",
        "content": (
            "You are a precise Python project generator. "
            "Generate ONLY the contents of the requested file.\n\n"
            "RULES:\n"
            "- Output ONLY Python source code for that single file.\n"
            "- NO markdown fences, NO comments explaining what you did.\n"
            "- Implement the functions/classes described.\n"
        ),
    }

    file_context = {
        "path": path,
        "description": description,
        "functions": functions,
    }

    user_msg = {
        "role": "user",
        "content": (
            f"Overall project request:\n{project_prompt}\n\n"
            f"Project summary:\n{summary}\n\n"
            "Generate ONLY the code for this file as valid Python source:\n"
            f"{json.dumps(file_context, ensure_ascii=False)}"
        ),
    }

    raw = await _call_llm(
        [system_msg, user_msg],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    clean = re.sub(r"```(?:python)?|```", "", raw).strip()
    return clean


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/generate", response_model=AutoFixResult)
async def generate_code(request: CodeRequest):
    global client
    if client is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    return await auto_fix_loop(request.prompt, request.max_iterations)


@app.post("/generate_project", response_model=ProjectGenerationResult)
async def generate_project(request: ProjectDesignRequest):
    """
    Multi-step project generation that works within a 32K context limit:

    1) Ask the model to DESIGN the project (list of files) as JSON.
    2) For each file, call the model again with only the project summary + that file's spec.
    """
    design = await design_project(request)
    files = design.get("files") or []

    generated_files: list[GeneratedFile] = []
    errors: list[str] = []

    for f in files:
        path = f.get("path", "app.py")
        try:
            code = await generate_file_code(
                project_prompt=request.prompt,
                design=design,
                file_spec=f,
                max_tokens=request.max_tokens_per_file,
                temperature=request.temperature,
            )
            generated_files.append(GeneratedFile(path=path, code=code))
        except HTTPException as e:
            errors.append(f"{path}: {e.detail}")
        except Exception as e:
            errors.append(f"{path}: {str(e)}")

    return ProjectGenerationResult(
        files=generated_files,
        design_json=json.dumps(design, ensure_ascii=False, indent=2),
        errors=errors,
    )


if __name__ == "__main__":
    uvicorn.run("codegen-server:app", host="0.0.0.0", port=8000)
