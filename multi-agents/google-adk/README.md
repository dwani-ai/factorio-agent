Multi Agent System with Google ADK


- 
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


LITELLM_MODEL_NAME="openai/gemma3" 
LITELLM_API_BASE="https://qwen-api"
LITELLM_API_KEY="sk-dummy"


- check AI inference
adk run test_api 

adk run starter-agents



https://codelabs.developers.google.com/codelabs/production-ready-ai-with-gc/3-developing-agents/build-a-multi-agent-system-with-adk#0


https://github.com/GoogleCloudPlatform/devrel-demos.git

git clone --depth 1 https://github.com/GoogleCloudPlatform/devrel-demos.git devrel-demos-multiagent-lab
