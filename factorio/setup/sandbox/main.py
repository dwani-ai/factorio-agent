from openai import OpenAI


import os 
client = OpenAI(
    api_key=os.environ["QWEN_API_KEY"],
    base_url=os.environ["QWEN_BASE_URL"],
)


def ask_llm(prompt: str, max_tokens: int = 200):
    try:
        response = client.chat.completions.create(
            model="qwen3-coder",  # or whatever alias/model name your server uses
            messages=[
                {"role": "system", "content": """You are a precise Python code generator. 
                Respond with EXACTLY ONE complete, executable Python code variant. 
                No explanations, no alternatives, no markdown, no comments, no tests—just the raw code."""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,      # optional - adjust as needed
            top_p=0.9,
            # stream=False,       # set to True later if you want streaming
        )

        # Extract the generated text
        content = response.choices[0].message.content.strip()

        print("Response from model:")
        print("-" * 70)
        print(content)
        print("-" * 70)

        # Optional: show usage stats
        print("\nUsage:", response.usage)

        return content

    except Exception as e:
        print(f"Error calling LLM: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print("Response details:", e.response.text)
        return None


if __name__ == "__main__":
    prompt = "Write a Python function to reverse a string"
    result = ask_llm(prompt, max_tokens=200)
    
    if result:
        # Pipe LLM output to Docker sandbox (secure, ephemeral execution)
        import subprocess
        cmd = [
            "echo", result, "|", "docker", "run", "--rm", "-i",
            "--network", "none", "--memory=256m", "--cpus=1",
            "--read-only", "--user", "1000:1000",
            "python:3.12-slim", "python", "-"
        ]
        proc = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        print("\nDocker sandbox output:")
        print(proc.stdout)
        if proc.stderr:
            print("Errors:", proc.stderr)
