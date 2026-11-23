#!/bin/bash
# Long-running Ollama server (gpt-oss:20b) holding both GPUs inside SLURM.
# Submit: sbatch scripts/slurm/ollama.sbatch   Stop: scancel -n ollama-gptoss
#SBATCH -J ollama-gptoss
#SBATCH -p xcpu
#SBATCH --gres=gpu:2
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -o logs/ollama-%j.log

# Vulkan on both GPUs: one Ollama runner can't mix CUDA (4060) and Vulkan (TITAN X: driver < 570 for CUDA)
export CUDA_VISIBLE_DEVICES=-1
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_MODELS=$HOME/.ollama-models
exec /usr/local/bin/ollama serve
