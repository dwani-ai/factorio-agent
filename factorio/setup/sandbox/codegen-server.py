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

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/generate", response_model=AutoFixResult)
async def generate_code(request: CodeRequest):
    global client
    if client is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return await auto_fix_loop(request.prompt, request.max_iterations)

if __name__ == "__main__":
    uvicorn.run("codegen-server:app", host="0.0.0.0", port=8000)
