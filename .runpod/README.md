![ComfyUI Worker Banner](https://cpjrphpz3t5wbwfe.public.blob.vercel-storage.com/worker-comfyui_banner-CDZ6JIEByEePozCT1ZrmeVOsN5NX3U.jpeg)

---

Run [ComfyUI](https://github.com/comfyanonymous/ComfyUI) workflows as a serverless endpoint.

---

[![RunPod](https://api.runpod.io/badge/runpod-workers/worker-comfyui)](https://www.runpod.io/console/hub/runpod-workers/worker-comfyui)

---

## What is included?

This worker comes with the **FLUX.1-dev-fp8** (`flux1-dev-fp8.safetensors`) model pre-installed and works only with this model when deployed from the hub. If you want to use a different model, you have to [deploy the endpoint](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/deployment.md) using one of these pre-defined Docker images:

- `runpod/worker-comfyui:<version>-base` - Clean ComfyUI install with no models
- `runpod/worker-comfyui:<version>-flux1-schnell` - FLUX.1 schnell model
- `runpod/worker-comfyui:<version>-flux1-dev` - FLUX.1 dev model
- `runpod/worker-comfyui:<version>-sdxl` - Stable Diffusion XL model
- `runpod/worker-comfyui:<version>-sd3` - Stable Diffusion 3 medium model

Replace `<version>` with the latest release version from [GitHub Releases](https://github.com/runpod-workers/worker-comfyui/releases)

If you need a different model or you have a LoRA or need custom nodes, then please follow our [Customization Guide](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md) to create your own custom worker.

## Usage

The worker accepts the following input parameters:

| Parameter  | Type     | Default | Required | Description                                                                                                                                                                                                                                    |
| :--------- | :------- | :------ | :------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workflow` | `object` | `None`  | **Yes**  | The entire ComfyUI workflow in the API JSON format. See the main project [README.md](https://github.com/runpod-workers/worker-comfyui#how-to-get-the-workflow-from-comfyui) for instructions on how to export this from the ComfyUI interface. |
| `images`   | `array`  | `[]`    | No       | An optional array of input images. Each image object should contain `name` (string, required, filename to reference in the workflow) and `image` (string, required, base64-encoded image data).                                                |

> [!NOTE]
> The `input.images` array has specific size constraints based on RunPod API limits (10MB for `/run`, 20MB for `/runsync`). See the main [README.md](https://github.com/runpod-workers/worker-comfyui#inputimages) for details.

### Example Request

This example uses a simplified workflow (replace with your actual workflow JSON).

```json
{
  "input": {
    "workflow": {
      "6": {
        "inputs": {
          "text": "anime cat with massive fluffy fennec ears and a big fluffy tail blonde messy long hair blue eyes wearing a construction outfit placing a fancy black forest cake with candles on top of a dinner table of an old dark Victorian mansion lit by candlelight with a bright window to the foggy forest and very expensive stuff everywhere there are paintings on the walls",
          "clip": ["30", 1]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
          "title": "CLIP Text Encode (Positive Prompt)"
        }
      },
      "8": {
        "inputs": {
          "samples": ["31", 0],
          "vae": ["30", 2]
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
      },
      "27": {
        "inputs": {
          "width": 512,
          "height": 512,
          "batch_size": 1
        },
        "class_type": "EmptySD3LatentImage",
        "_meta": {
          "title": "EmptySD3LatentImage"
        }
      },
      "30": {
        "inputs": {
          "ckpt_name": "flux1-dev-fp8.safetensors"
        },
        "class_type": "CheckpointLoaderSimple",
        "_meta": {
          "title": "Load Checkpoint"
        }
      },
      "31": {
        "inputs": {
          "seed": 243057879077961,
          "steps": 10,
          "cfg": 1,
          "sampler_name": "euler",
          "scheduler": "simple",
          "denoise": 1,
          "model": ["30", 0],
          "positive": ["35", 0],
          "negative": ["33", 0],
          "latent_image": ["27", 0]
        },
        "class_type": "KSampler",
        "_meta": {
          "title": "KSampler"
        }
      },
      "33": {
        "inputs": {
          "text": "",
          "clip": ["30", 1]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
          "title": "CLIP Text Encode (Negative Prompt)"
        }
      },
      "35": {
        "inputs": {
          "guidance": 3.5,
          "conditioning": ["6", 0]
        },
        "class_type": "FluxGuidance",
        "_meta": {
          "title": "FluxGuidance"
        }
      },
      "38": {
        "inputs": {
          "images": ["8", 0]
        },
        "class_type": "PreviewImage",
        "_meta": {
          "title": "Preview Image"
        }
      },
      "40": {
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
