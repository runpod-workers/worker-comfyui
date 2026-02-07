# ComfyUI Workflows

A curated collection of [ComfyUI](https://github.com/comfyanonymous/ComfyUI) workflows for image and video generation.

## Folder Structure

```
workflows/
  txt2img/        Text-to-image generation
  img2img/        Image-to-image transformation
  inpainting/     Inpainting and outpainting
  upscaling/      Upscaling and enhancement
  video/          Video generation (AnimateDiff, SVD, etc.)
  controlnet/     ControlNet-based workflows
  lora/           LoRA training and usage workflows
  custom/         Experimental or uncategorized workflows
examples/
  inputs/         Sample input images for testing workflows
  outputs/        Sample output images showing expected results
```

## Adding a Workflow

1. Export your workflow from ComfyUI using **Workflow > Export (API)**.
2. Place the exported `.json` file in the appropriate category folder under `workflows/`.
3. Name the file descriptively, e.g. `flux1-schnell-basic.json` or `sdxl-hires-fix.json`.
4. Optionally add example input/output images to `examples/`.

### Naming Convention

Use lowercase with hyphens. Include the base model when relevant:

```
workflows/txt2img/sdxl-basic.json
workflows/txt2img/flux1-schnell-basic.json
workflows/controlnet/sdxl-canny-edge.json
workflows/upscaling/4x-ultrasharp.json
```

## Using a Workflow

1. Open ComfyUI in your browser.
2. Drag and drop the `.json` file onto the ComfyUI canvas, or use **Workflow > Import**.
3. Adjust parameters (prompts, models, seeds, etc.) as needed.
4. Queue the workflow to generate.

### Using via API

Workflows can also be submitted via the RunPod serverless API. See the `test_resources/` directory for API input examples, or use the workflow JSON directly as the `input.workflow` field in your API request.

## Workflow Format

All workflows use the **ComfyUI API format** (exported via `Export (API)`), not the UI format. The API format uses numeric node IDs and is suitable for both programmatic use and re-import into ComfyUI.

## Required Models

Each workflow depends on specific models (checkpoints, VAEs, LoRAs, ControlNet models, etc.). Check the node configurations within each workflow JSON to identify which models are needed. Common model sources:

- [Hugging Face](https://huggingface.co/)
- [CivitAI](https://civitai.com/)

## License

See [LICENSE](LICENSE) for details.
