#!/bin/bash
# Run a command inside the Ollama job's allocation, so it can use the same GPUs.
# Usage: scripts/slurm/run.sh .venv/bin/python -m image_search selftest
set -e
JOB=$(squeue -h -u "$USER" -n ollama-gptoss -t RUNNING -o %i | head -1)
[ -n "$JOB" ] || { echo "ollama-gptoss job not running: sbatch scripts/slurm/ollama.sbatch" >&2; exit 1; }
exec srun --jobid="$JOB" --overlap "$@"
