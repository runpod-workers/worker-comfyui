#!/usr/bin/env bash

set -e

SNAPSHOT_FILE=$(ls /*snapshot*.json 2>/dev/null | head -n 1)

if [ -z "$SNAPSHOT_FILE" ]; then
    echo "worker-comfyui: No snapshot file found. Exiting..."
    exit 0
fi

echo "worker-comfyui: restoring snapshot: $SNAPSHOT_FILE"

comfy --workspace /comfyui node restore-snapshot "$SNAPSHOT_FILE" --pip-non-url

echo "worker-comfyui: restored snapshot file: $SNAPSHOT_FILE"