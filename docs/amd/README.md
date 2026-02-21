AMD GPU

https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-qwen3-coder-next-on-amd-instinct-gpus.html

docker run -it \
  --entrypoint /bin/bash \
  --device /dev/dri \
  --device /dev/kfd \
  --network=host \
  --ipc=host \
  --group-add video \
  --security-opt seccomp=unconfined \
  -v $(pwd):/workspace \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --name Qwen3-Coder-Next \
  vllm/vllm-openai-rocm:v0.15.0

  vllm serve Qwen/Qwen3-Coder-Next --tensor-parallel-size 2   --enable-auto-tool-choice --tool-call-parser qwen3_coder