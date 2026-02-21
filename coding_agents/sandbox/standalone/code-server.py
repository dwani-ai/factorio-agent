from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import re
import subprocess
from openai import OpenAI
import uvicorn

app = FastAPI(title="CodeGen Sandbox API")

# Initialize OpenAI client with Qwen endpoint
client = OpenAI(
    api_key=os.environ["QWEN_API_KEY"],
    base_url=os.environ["QWEN_BASE_URL"],
)

class CodeRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 200

@app.post("/generate")
async def generate_and_execute(request: CodeRequest):
    try:
        response = client.chat.completions.create(
            model="qwen3-coder",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a Python code generator. RULES:
- Output ONLY valid Python code that runs immediately when pasted into Python interpreter
- NO ``` markdown fences, NO # comments, NO explanations  
- Include function definition + test call + print(result)
- Example for "reverse string": def reverse_string(s):return s[::-1];print(reverse_string("hello"))
EVERY response MUST be directly executable Python ONLY."""
                },
                {"role": "user", "content": request.prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=0.7,
            top_p=0.9,
        )

        content = response.choices[0].message.content.strip()

        
        
        # Clean code aggressively - remove markdown and comments
        clean_code = re.sub(r'```python|```', '', content).strip()
        clean_code = re.sub(r'#.*', '', clean_code)
        clean_code = re.sub(r'^\s*\n', '', clean_code, flags=re.MULTILINE).strip()
        
        # Docker sandbox execution with security constraints
        cmd = [
            "docker", "run", "--rm", "-i", 
            "--network", "none", 
            "--memory", "256m", 
            "--cpus", "0.5",
            "python:3.12-slim", 
            "python", "-"
        ]
        
        proc = subprocess.Popen(
            cmd, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        stdout, stderr = proc.communicate(input=clean_code, timeout=30)
        
        return {
            "success": True,
            "final_answer": stdout.strip() or "No output",
            "clean_code": clean_code,
            "raw_response": content,
            "sandbox_stderr": stderr.strip() if stderr and stderr.strip() else None
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "final_answer": "Execution timeout",
            "error": "Code execution exceeded time limit"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CodeGen Sandbox"}

if __name__ == "__main__":
    # FIXED: Pass app as import string for reload to work
    uvicorn.run(
        "code-server:app",  # Import string format: "filename:instance"
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Now works without warning
        log_level="info"
    )
