#!/usr/bin/env bash
# Runs on the rented host: makes `docker run --gpus` work (this provider's image lacked the NVIDIA container toolkit
# on 2026-09-15) and installs ffprobe.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
echo "== host"; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | sort | uniq -c
free -g | head -2; df -h "$HOME" | tail -1; nproc
if ! command -v ffprobe >/dev/null; then sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg >/dev/null; fi
if ! docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L >/dev/null 2>&1; then
  echo "== installing the NVIDIA container toolkit"
  if ! command -v nvidia-ctk >/dev/null; then
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
      sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |
      sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
    sudo apt-get update -qq && sudo apt-get install -y -qq nvidia-container-toolkit >/dev/null
  fi
  sudo nvidia-ctk runtime configure --runtime=docker >/dev/null
  sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml >/dev/null 2>&1 || true
  sudo systemctl restart docker
  sleep 3
fi
docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L | head -8
echo "prep done"
