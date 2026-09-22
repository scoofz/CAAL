#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
release=prism-b10709-9a9394a
revision=6ed5e12bf84b7a63069882c91dd9e9218647d17b
filename=Ternary-Bonsai-2-27B-PTQ1_0.gguf
mkdir -p .local/bonsai/bin .local/bonsai/models
archive=".local/bonsai/llama-${release}-bin-ubuntu-vulkan-x64.tar.gz"
if [ ! -f "$archive" ]; then
  curl -fL --retry 3 "https://github.com/PrismML-Eng/llama.cpp/releases/download/${release}/llama-${release}-bin-ubuntu-vulkan-x64.tar.gz" -o "$archive.part"
  mv "$archive.part" "$archive"
fi
tar -xzf "$archive" -C .local/bonsai/bin
if [ ! -f ".local/bonsai/models/$filename" ]; then
  curl -fL --retry 3 -C - "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/resolve/${revision}/${filename}" -o ".local/bonsai/models/$filename.part"
  mv ".local/bonsai/models/$filename.part" ".local/bonsai/models/$filename"
fi
printf '%s  %s\n' '53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3' ".local/bonsai/models/$filename" | sha256sum -c -
