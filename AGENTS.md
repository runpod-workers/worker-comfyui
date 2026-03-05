# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**worker-comfyui** is a serverless API wrapper for ComfyUI running on RunPod. It accepts workflow JSON via REST API, executes image generation through ComfyUI, and returns images as base64 strings or S3 URLs.

## Common Commands

```bash
# Run unit tests
python -m unittest discover tests/

# Run specific test
python -m unittest tests.test_handler.TestRunpodWorkerComfy.test_s3_upload

# Build Docker image (dev, no models - fastest)
docker build --build-arg MODEL_TYPE=base -t runpod/worker-comfyui:dev .

# Build with models (e.g., sdxl, flux1-dev, sd3)
docker build --build-arg MODEL_TYPE=sdxl -t runpod/worker-comfyui:dev .

# Local development with docker-compose
docker-compose down && docker build --build-arg MODEL_TYPE=base -t runpod/worker-comfyui:dev . && docker-compose up

# Test API locally (after docker-compose up)
curl -X POST http://localhost:8000/runsync -H "Content-Type: application/json" -d @test_input.json

# Build all image variants using docker-bake
docker buildx bake -f docker-bake.hcl
```

**Local endpoints** (when running docker-compose):
- Worker API: http://localhost:8000 (FastAPI docs at /docs)
- ComfyUI UI: http://localhost:8188

## Architecture

### Core Files

- `handler.py` - Main RunPod handler; receives jobs, communicates with ComfyUI via HTTP/WebSocket, returns results
- `src/start.sh` - Container entrypoint; starts ComfyUI server, then handler
- `src/network_volume.py` - Network volume diagnostics utilities
- `src/extra_model_paths.yaml` - ComfyUI model path configuration for network volumes

### Job Execution Flow

1. RunPod SDK calls `handler(job)` with workflow JSON + optional input images
2. `validate_input()` checks required fields
3. `check_server()` verifies ComfyUI HTTP API is reachable
4. `upload_images()` sends base64 images to ComfyUI's `/upload/image` endpoint
5. WebSocket connection established to `ws://127.0.0.1:8188/ws`
6. `queue_workflow()` POSTs workflow to `/prompt`
7. Handler monitors WebSocket for execution progress/completion
8. `get_history()` retrieves results from `/history/<prompt_id>`
9. Images processed (base64 encode or S3 upload) and returned

### Docker Build System

Multi-stage Dockerfile with `MODEL_TYPE` build arg:
- `base` stage: Python 3.12, ComfyUI via comfy-cli, RunPod SDK
- `downloader` stage: Downloads models based on MODEL_TYPE
- `final` stage: Combines base + models

Available MODEL_TYPE values: `base`, `sdxl`, `sd3`, `flux1-schnell`, `flux1-dev`, `flux1-dev-fp8`, `z-image-turbo`

### Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REFRESH_WORKER` | `false` | Restart pod after each job |
| `SERVE_API_LOCALLY` | `false` | Enable local HTTP server for testing |
| `COMFY_ORG_API_KEY` | - | API key for Comfy.org API Nodes |
| `WEBSOCKET_RECONNECT_ATTEMPTS` | `5` | WebSocket reconnection retries |
| `WEBSOCKET_RECONNECT_DELAY_S` | `3` | Delay between retries |
| `NETWORK_VOLUME_DEBUG` | `false` | Enable network volume diagnostics |
| `BUCKET_ENDPOINT_URL` | - | S3 endpoint (enables S3 upload) |
| `BUCKET_ACCESS_KEY_ID` | - | S3 access key |
| `BUCKET_SECRET_ACCESS_KEY` | - | S3 secret key |

## API Format

**Input:**
```json
{
  "input": {
    "workflow": { /* ComfyUI API-format workflow JSON */ },
    "images": [{"name": "input.png", "image": "base64..."}]
  }
}
```

**Output (v5.0.0+):**
```json
{
  "output": {
    "images": [
      {"filename": "ComfyUI_00001_.png", "type": "base64", "data": "..."}
    ]
  }
}
```

Get workflow JSON: In ComfyUI, use `Workflow > Export (API)`.

## Development Conventions

- **Always rebuild Docker** after handler.py changes before testing with docker-compose
- **Use `--platform linux/amd64`** when building for RunPod deployment
- **Environment variables** for all external configuration
- **WebSocket** for ComfyUI status monitoring (not HTTP polling)
- **Parse ComfyUI validation errors** for user-friendly messages
- **No automated linting** - follow PEP 8 conventions

## Model Type Detection (for workflow parsing)

Node type to model category mappings:
- `UpscaleModelLoader` → `upscale_models`
- `VAELoader` → `vae`
- `UNETLoader`, `UnetLoaderGGUF`, `Hy3DModelLoader` → `diffusion_models`
- `DualCLIPLoader`, `TripleCLIPLoader` → `text_encoders`
- `LoraLoader` → `loras`

## Extending with Custom Nodes

```dockerfile
FROM runpod/worker-comfyui:5.1.0-base
RUN comfy-node-install comfyui-kjnodes comfyui-ic-light
```

## Adding Custom Models

```dockerfile
RUN comfy model download --url <huggingface-url> \
  --relative-path models/checkpoints \
  --filename my_model.safetensors
```
