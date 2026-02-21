from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import resource
import signal
import os
import sys
import uvicorn

app = FastAPI(title="Secure Process Sandbox")

class ExecuteRequest(BaseModel):
    code: str

def sandboxed_exec(code: str):
    """Execute untrusted code with strict limits"""
    
    # Set resource limits BEFORE subprocess
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))      # 2 CPU seconds
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024**2, 128 * 1024**2))  # 128MB
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))           # 1MB files
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))                     # 10 processes
    
    # Create minimal environment
    env = {
        "PYTHONPATH": "",
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        "PATH": "/usr/local/bin:/usr/bin:/bin"
    }
    
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", code],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/tmp",
            env=env,
            preexec_fn=os.setsid  # Session leader for killpg
        )
        
        stdout, stderr = proc.communicate(timeout=10)
        
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode('utf-8', errors='ignore').strip(),
            "stderr": stderr.decode('utf-8', errors='ignore').strip(),
            "exit_code": proc.returncode
        }
        
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        return {
            "success": False,
            "stdout": "",
            "stderr": "Execution timeout (10s)",
            "exit_code": 408
        }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/execute")
async def execute_code(request: ExecuteRequest):
    try:
        return sandboxed_exec(request.code)
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Sandbox error: {str(e)}",
            "exit_code": 500
        }

if __name__ == "__main__":
    uvicorn.run("sandbox-server:app", host="0.0.0.0", port=8001)
