#!/bin/bash
#SBATCH --job-name=qwen38_prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/qwen38_27b_gguf_v1
#SBATCH --output=/home/yeliheng/grasp_server/qwen38_27b_gguf_v1/prepare-%j.log
set -euo pipefail
ROOT=/home/yeliheng/grasp_server/qwen38_27b_gguf_v1
MODEL=Qwen3.8-27B-UD-Q4_K_M.gguf
SHA=322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482
REV=0693dbfb915f33233818373b5f6969396658d02c
trap 'jobs -pr | xargs -r kill' EXIT
mkdir -p models
(
    curl --fail --location --retry 3 --retry-delay 3 --continue-at - \
      --output "models/$MODEL.part" \
      "https://modelscope.cn/api/v1/models/unsloth/Qwen3.8-27B-GGUF/repo?Revision=master&FilePath=$MODEL" \
      > download.log 2>&1
    printf '%s  %s\n' "$SHA" "models/$MODEL.part" | sha256sum --check
    mv "models/$MODEL.part" "models/$MODEL"
    printf 'model_sha256=%s\n' "$SHA" > model-ready.txt
) &
DOWNLOAD_PID=$!
curl --fail --location --retry 3 --max-time 300 \
  "https://codeload.github.com/ggml-org/llama.cpp/tar.gz/$REV" --output source.tar.gz
sha256sum source.tar.gz > source-archive.sha256
mkdir source
tar -xzf source.tar.gz --strip-components=1 -C source
cmake -S source -B build -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70 -DGGML_CUDA_FORCE_MMQ=ON \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_APP=OFF \
  -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_OPENSSL=OFF
cmake --build build --parallel 8 --target llama-server
build/bin/llama-server --version > engine-version.txt 2>&1
wait "$DOWNLOAD_PID"
sha256sum build/bin/llama-server > engine.sha256
printf 'preparation_completed\n' > ready.txt

