![ComfyUI Worker Banner](https://cpjrphpz3t5wbwfe.public.blob.vercel-storage.com/worker-comfyui_banner-CDZ6JIEByEePozCT1ZrmeVOsN5NX3U.jpeg)

---

Run [ComfyUI](https://github.com/comfyanonymous/ComfyUI) workflows as a serverless endpoint.

---

[![RunPod](https://api.runpod.io/badge/runpod-workers/worker-comfyui)](https://www.runpod.io/console/hub/runpod-workers/worker-comfyui)

---

## What is included?

This worker comes with the **FLUX.2 klein 9B** (`flux-2-klein-9b-Q5_K_M.gguf`) model pre-installed and **works only with this specific model** when deployed from the hub.

## Want to use a different model?

**The hub deployment only supports FLUX.2 klein 9B (Q5_K_M GGUF).** If you need any other model, custom nodes, or LoRAs, you have two options:

### Option 1: ComfyUI-to-API (Easiest & Recommended)

[**ComfyUI-to-API**](https://comfy.getrunpod.io) automatically converts your ComfyUI workflow into a deployment-ready GitHub repository with all dependencies configured.

**Quick Steps:**

1. Export your workflow from ComfyUI using `Comfy > File > Export` (**not** `Export (API)`)
2. Upload to [comfy.getrunpod.io](https://comfy.getrunpod.io) - It analyzes your workflow
3. Get a custom GitHub repository with everything configured
4. Deploy using RunPod's GitHub integration

**See the full guide:** [ComfyUI-to-API](https://docs.runpod.io/community-solutions/comfyui-to-api/overview)

### Option 2: Manual Customization

Follow the [Customization Guide](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md) to manually create your own custom worker by editing Dockerfiles and managing dependencies yourself.

## Configuration

For all available environment variables including Comfy.org API key, S3 upload, logging, and debugging options, see the [Configuration Guide](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/configuration.md).

## Usage

The worker accepts the following input parameters:

| Parameter           | Type     | Default | Required | Description                                                                                                                                                                                                                                    |
| :------------------ | :------- | :------ | :------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workflow`          | `object` | `None`  | **Yes**  | The entire ComfyUI workflow in the API JSON format. See the main project [README.md](https://github.com/runpod-workers/worker-comfyui#how-to-get-the-workflow-from-comfyui) for instructions on how to export this from the ComfyUI interface. |
| `images`            | `array`  | `[]`    | No       | An optional array of input images. Each image object should contain `name` (string, required, filename to reference in the workflow) and `image` (string, required, base64-encoded image data).                                                |
| `comfy_org_api_key` | `string` | `None`  | No       | Optional Comfy.org API key for ComfyUI API Nodes. Overrides the `COMFY_ORG_API_KEY` environment variable if set.                                                                                                                               |

> [!NOTE]
> The `input.images` array has specific size constraints based on RunPod API limits (10MB for `/run`, 20MB for `/runsync`). See the main [README.md](https://github.com/runpod-workers/worker-comfyui#inputimages) for details.

### Example Request

This example uses a simplified workflow (replace with your actual workflow JSON).

```json
{
  "input": {
    "workflow": {
      "1": {
        "inputs": {
          "unet_name": "flux-2-klein-9b-Q5_K_M.gguf"
        },
        "class_type": "UnetLoaderGGUF",
        "_meta": {
          "title": "Load GGUF Model"
        }
      },
      "2": {
        "inputs": {
          "clip_name": "qwen_3_8b_fp8mixed.safetensors",
          "type": "flux2"
        },
        "class_type": "CLIPLoader",
        "_meta": {
          "title": "Load Text Encoder"
        }
      },
      "3": {
        "inputs": {
          "vae_name": "flux2-vae.safetensors"
        },
        "class_type": "VAELoader",
        "_meta": {
          "title": "Load VAE"
        }
      },
      "4": {
        "inputs": {
          "text": "anime cat with massive fluffy fennec ears and a big fluffy tail blonde messy long hair blue eyes wearing a construction outfit placing a fancy black forest cake with candles on top of a dinner table of an old dark Victorian mansion lit by candlelight with a bright window to the foggy forest and very expensive stuff everywhere there are paintings on the walls",
          "clip": ["2", 0]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
          "title": "CLIP Text Encode (Positive Prompt)"
        }
      },
      "5": {
        "inputs": {
          "text": "",
          "clip": ["2", 0]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
          "title": "CLIP Text Encode (Negative Prompt)"
        }
      },
      "6": {
        "inputs": {
          "width": 1024,
          "height": 1024,
          "batch_size": 1
        },
        "class_type": "EmptyLatentImage",
        "_meta": {
          "title": "Empty Latent Image"
        }
      },
      "7": {
        "inputs": {
          "seed": 243057879077961,
          "steps": 4,
          "cfg": 1,
          "sampler_name": "euler",
          "scheduler": "simple",
          "denoise": 1,
          "model": ["1", 0],
          "positive": ["4", 0],
          "negative": ["5", 0],
          "latent_image": ["6", 0]
        },
        "class_type": "KSampler",
        "_meta": {
          "title": "KSampler"
        }
      },
      "8": {
        "inputs": {
          "samples": ["7", 0],
          "vae": ["3", 0]
        },
        "class_type": "VAEDecode",
        "_meta": {
          "title": "VAE Decode"
        }
      },
      "9": {
        "inputs": {
          "filename_prefix": "ComfyUI",
          "images": ["8", 0]
        },
        "class_type": "SaveImage",
        "_meta": {
          "title": "Save Image"
        }
      }
    }
  }
}
```

### Example Response

```json
{
  "delayTime": 2188,
  "executionTime": 2297,
  "id": "sync-c0cd1eb2-068f-4ecf-a99a-55770fc77391-e1",
  "output": {
    "message": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABAAAAAQACAIAAADwf7zU...",
    "status": "success"
  },
  "status": "COMPLETED"
}
```
