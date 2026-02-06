from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import re
import httpx
import uvicorn
from openai import OpenAI
from contextlib import asynccontextmanager

# Declare global client FIRST
client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client  # Reference global - NO assignment here
    
    # Startup: Initialize OpenAI client
    try:
        client = OpenAI(
            api_key=os.environ["QWEN_API_KEY"],
            base_url=os.environ["QWEN_BASE_URL"],
        )
        print("✅ OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ OpenAI client init failed: {e}")
        client = None
    
    yield
    
    # Shutdown
    client = None
    print("🔌 OpenAI client closed")

app = FastAPI(title="CodeGen API", lifespan=lifespan)

SANDBOX_SERVICE_URL = os.environ.get("SANDBOX_URL", "http://localhost:8001")

class CodeRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 200

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "codegen"}

@app.post("/generate")
async def generate_code(request: CodeRequest):
    global client
    
    if client is None:
        raise HTTPException(status_code=503, detail="OpenAI client not ready")
    
    try:
        print(f"Generating code for: {request.prompt[:50]}...")
        
        response = client.chat.completions.create(
            model="qwen3-coder",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a Python code generator. RULES:
- Output ONLY valid Python code that runs immediately when pasted into Python interpreter
- NO ``` markdown fences, NO # comments, NO explanations  
- Include function definition + test call + print(result)
- Example: def reverse_string(s):return s[::-1];print(reverse_string("hello"))
EVERY response MUST be directly executable Python ONLY."""
                },
                {"role": "user", "content": request.prompt}
            ],
            max_tokens=request.max_tokens or 200,
            temperature=0.7,
            top_p=0.9,
        )
        
        # Robust content extraction
        content = response.choices[0].message.content.strip()
        
        # Clean code
        clean_code = re.sub(r'```(?:python)?|```', '', content).strip()
        clean_code = re.sub(r'#.*?(?=\n|$)', '', clean_code, flags=re.MULTILINE).strip()
        
        print(f"Executing code ({len(clean_code)} chars)...")
        
        # Call sandbox service
        async with httpx.AsyncClient(timeout=45.0) as http_client:
            sandbox_resp = await http_client.post(
                f"{SANDBOX_SERVICE_URL}/execute",
                json={"code": clean_code},
                timeout=30.0
            )
            sandbox_data = sandbox_resp.json()
        
        return {
            "success": True,
            "final_answer": sandbox_data["stdout"].strip() or "No output",
            "clean_code": clean_code,
            "raw_response": content,
            "sandbox_stderr": sandbox_data.get("stderr")
        }
        
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Sandbox service unavailable")
    except Exception as e:
        print(f"Error in generate_code: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("codegen-server:app", host="0.0.0.0", port=8000, reload=True)
