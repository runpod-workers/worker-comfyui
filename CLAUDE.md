# CLAUDE.md

This file provides context for Claude Code when working in this repository.

## Project Overview

This repository stores ComfyUI workflows organized by category. It also contains the RunPod serverless worker infrastructure for executing these workflows via API.

## Repository Layout

- `workflows/` - ComfyUI workflow JSON files, organized by category (txt2img, img2img, inpainting, upscaling, video, controlnet, lora, custom)
- `examples/` - Sample input/output images for testing and documentation
- `handler.py` - RunPod serverless handler that executes ComfyUI workflows
- `src/` - Supporting source code (startup scripts, model path config)
- `scripts/` - Utility shell scripts for ComfyUI manager and node installation
- `tests/` - Test suite for the handler
- `test_resources/` - Test fixtures including sample workflows and images
- `docs/` - Project documentation (deployment, configuration, customization, development)
- `.github/` - GitHub Actions CI/CD workflows and issue templates
- `Dockerfile` / `docker-bake.hcl` / `docker-compose.yml` - Container build configuration

## Workflow Files

- All workflows use the **ComfyUI API format** (numeric node IDs), not the UI format
- Exported via ComfyUI's `Workflow > Export (API)` menu
- Stored as `.json` files
- Named with lowercase-hyphen convention, including the base model: e.g. `sdxl-basic.json`, `flux1-schnell-basic.json`

## Key Commands

```bash
# Run tests
python -m pytest tests/

# Build Docker image
docker compose build

# Run locally
docker compose up
```

## Conventions

- Workflow filenames: lowercase, hyphen-separated, model name prefix when relevant
- Workflow categories map to subdirectories under `workflows/`
- Python code follows standard formatting (see existing code style)
- Commit messages should be descriptive and reference the workflow or change being made
