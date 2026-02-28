#!/usr/bin/env bash

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"

# Start nginx immediately so port 8188 is answered from the first second,
# replacing the CloudFlare 502 window with the loading page.
echo "worker-comfyui: Starting nginx"
nginx

# Ensure ComfyUI-Manager runs in offline network mode inside the container
comfy-manager-set-mode offline || echo "worker-comfyui - Could not set ComfyUI-Manager network_mode" >&2

echo "worker-comfyui: Starting ComfyUI"

# Allow operators to tweak verbosity; default is DEBUG.
: "${COMFY_LOG_LEVEL:=DEBUG}"

# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    python -u /comfyui/main.py --port 8189 --disable-auto-launch --disable-metadata --listen --verbose "${COMFY_LOG_LEVEL}" --log-stdout 2>&1 | tee /tmp/comfyui.log &

    echo "worker-comfyui: Starting RunPod Handler"
    python -u /handler.py --rp_serve_api --rp_api_host=0.0.0.0
else
    python -u /comfyui/main.py --port 8189 --disable-auto-launch --disable-metadata --verbose "${COMFY_LOG_LEVEL}" --log-stdout 2>&1 | tee /tmp/comfyui.log &

    echo "worker-comfyui: Starting RunPod Handler"
    python -u /handler.py
fi
