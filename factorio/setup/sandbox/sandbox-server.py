from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os
import uvicorn

app = FastAPI(title="Secure Sandbox")

class ExecuteRequest(BaseModel):
    code: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sandbox"}

@app.post("/execute")
async def execute_code(request: ExecuteRequest):
    try:
        # Use subprocess instead of docker-py (simpler, more reliable)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(request.code)
            code_file = f.name
        
        # Secure Docker execution via subprocess
        cmd = [
            "docker", "run", "--rm", "-i",
            "--network", "none",
            "--memory", "256m",
            "--cpus", "0.5",
            "python:3.12-slim",
            "sh", "-c", f"cat > /tmp/code.py && python /tmp/code.py"
        ]
        
        proc = subprocess.run(
            cmd,
            input=request.code,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        os.unlink(code_file)
        
        return {
            "success": True,
            "stdout": proc.stdout.strip() or "No output",
            "stderr": proc.stderr.strip() if proc.stderr.strip() else None
        }
        
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e)}

if __name__ == "__main__":
    uvicorn.run("sandbox-server:app", host="0.0.0.0", port=8001, reload=True)
