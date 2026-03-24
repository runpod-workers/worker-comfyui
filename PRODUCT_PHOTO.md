# Product Photography Setup

This fork adds a `product-photo` model type optimized for AI product photography on Amazon/e-commerce.

## What's Included

| Model | Purpose |
|-------|---------|
| Juggernaut XL v9 | High-quality photorealistic base model |
| IP-Adapter SD15 | Style transfer from product images |
| IP-Adapter Plus Face | Enhanced style preservation |
| ControlNet Depth | Camera angle/pose control |
| ControlNet Canny | Edge-based structural control |
| rembg | Automatic background removal |

## Deploy to RunPod Serverless

### 1. Build or Use Pre-built Image

**Option A: Use GitHub Container Registry (recommended)**
The GitHub Action automatically builds and pushes to:
```
ghcr.io/stellaraether/worker-comfyui:product-photo
```

**Option B: Build locally**
```bash
docker build \
  --build-arg MODEL_TYPE=product-photo \
  -t yourname/comfyui-product-photo:latest .

docker push yourname/comfyui-product-photo:latest
```

### 2. Create RunPod Endpoint

1. Go to RunPod Console → Serverless → New Endpoint
2. **Name**: `comfyui-product-photo`
3. **Image**: `ghcr.io/stellaraether/worker-comfyui:product-photo`
4. **GPU**: RTX 4090 (or A6000 for larger batches)
5. **Workers**: Min 0, Max 1 (start here)
6. **FlashBoot**: Enabled (cuts cold start by ~40%)
7. **Idle Timeout**: 10 seconds

### 3. Test with Python

```python
import requests
import json
import base64

API_KEY = "your_runpod_api_key"
ENDPOINT_ID = "your_endpoint_id"

def generate_product_photo(workflow_json, product_image_path=None):
    url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/run"
    
    payload = {"input": {"workflow": workflow_json}}
    
    if product_image_path:
        with open(product_image_path, "rb") as f:
            payload["input"]["product_image"] = base64.b64encode(f.read()).decode()
    
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload
    )
    return resp.json()["id"]

# Poll for result...
```

## Example Workflows

### Simple Product on White Background
```json
{
  "3": {
    "inputs": {"text": "professional product photo, dog treat ball, pure white background, studio lighting, soft shadows, 8k, commercial photography", "clip": ["4", 0]},
    "class_type": "CLIPTextEncode"
  },
  "4": {
    "inputs": {"ckpt_name": "juggernautXL_v9.safetensors"},
    "class_type": "CheckpointLoaderSimple"
  },
  "5": {
    "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
    "class_type": "EmptyLatentImage"
  },
  "6": {
    "inputs": {"seed": 12345, "steps": 25, "cfg": 7, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1, "model": ["4", 0], "positive": ["3", 0], "negative": ["3", 1], "latent_image": ["5", 0]},
    "class_type": "KSampler"
  },
  "8": {
    "inputs": {"samples": ["6", 0], "vae": ["4", 2]},
    "class_type": "VAEDecode"
  },
  "9": {
    "inputs": {"filename_prefix": "product", "images": ["8", 0]},
    "class_type": "SaveImage"
  }
}
```

### With IP-Adapter (Style Transfer)
Upload your product image first, then reference it in the workflow with IPAdapter nodes.

## Cold Start Times

| Model Type | First Request | Subsequent |
|------------|---------------|------------|
| product-photo | ~25-35 sec | ~15 sec |
| With FlashBoot | ~15-20 sec | ~15 sec |

## Cost Estimate

- RTX 4090: ~$0.00024/second
- 5 product photos: ~$0.015-0.02 (including cold start)
- 50 product photos (batched): ~$0.08-0.12

## Customizing

Edit `Dockerfile` to add more models:
```dockerfile
RUN if [ "$MODEL_TYPE" = "product-photo" ]; then \
    wget -q -O models/controlnet/control_v11p_sd15_openpose.safetensors ... && \
    ...
```

Then rebuild and push.

## Local Testing

```bash
# Start container locally
docker run -p 8188:8188 \
  -e COMFY_USER=admin \
  -e COMFY_PASS=password \
  ghcr.io/stellaraether/worker-comfyui:product-photo

# Access ComfyUI at http://localhost:8188
```
