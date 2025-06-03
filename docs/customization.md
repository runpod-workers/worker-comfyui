# Customization

This guide covers methods for adding your own models, custom nodes, and static input files into a custom `worker-comfyui`.

There are two primary methods for customizing your setup:

1.  **Custom Dockerfile (recommended):** Create your own `Dockerfile` starting `FROM` one of the official `worker-comfyui` base images. This allows you to bake specific custom nodes, models, and input files directly into your image using `comfy-cli` commands. **This method does not require forking the `worker-comfyui` repository.**
2.  **Network Volume:** Store models on a persistent network volume attached to your RunPod endpoint. This is useful if you frequently change models or have very large models you don't want to include in the image build process.

## Method 1: Custom Dockerfile

> [!NOTE]
>
> This method does NOT require forking the `worker-comfyui` repository.

This is the most flexible and recommended approach for creating reproducible, customized worker environments.

1.  **Create a `Dockerfile`:** In your own project directory, create a file named `Dockerfile`.
2.  **Start with a Base Image:** Begin your `Dockerfile` by referencing one of the official base images. Using the `-base` tag is recommended as it provides a clean ComfyUI install with necessary tools like `comfy-cli` but without pre-packaged models.
    ```Dockerfile
    # start from a clean base image (replace <version> with the desired [release](https://github.com/runpod/worker-comfyui/releases))
    FROM runpod/worker-comfyui:<version>-base
    ```
3.  **Install Custom Nodes:** Use the `comfy-node-install` (we had introduce our own cli tool here, as there is a [problem with comfy-cli not showing errors during installation](https://github.com/Comfy-Org/comfy-cli/pull/275)) command to add custom nodes by their name or URL, see [Comfy Registry](https://registry.comfy.org) to find the correct name. You can list multiple nodes.
    ```Dockerfile
    # install custom nodes using comfy-cli
    RUN comfy-node-install comfyui-kjnodes comfyui-ic-light
    ```
4.  **Download Models:** Use the `comfy model download` command to fetch models and place them in the correct ComfyUI directories.

    ```Dockerfile
    # download models using comfy-cli
    RUN comfy model download --url https://huggingface.co/KamCastle/jugg/resolve/main/juggernaut_reborn.safetensors --relative-path models/checkpoints --filename juggernaut_reborn.safetensors
    ```

> [!NOTE]
>
> Ensure you use the correct `--relative-path` corresponding to ComfyUI's model directory structure (starting with `models/<folder>`):
>
> checkpoints, clip, clip_vision, configs, controlnet, diffusers, embeddings, gligen, hypernetworks, loras, style_models, unet, upscale_models, vae, vae_approx, animatediff_models, animatediff_motion_lora, ipadapter, photomaker, sams, insightface, facerestore_models, facedetection, mmdets, instantid

5.  **Add Static Input Files (Optional):** If your workflows consistently require specific input images, masks, videos, etc., you can copy them directly into the image.

- Create an `input/` directory in the same folder as your `Dockerfile`.
- Place your static files inside this `input/` directory.
- Add a `COPY` command to your `Dockerfile`:

  ```Dockerfile
  # Copy local static input files into the ComfyUI input directory
  COPY input/ /comfyui/input/
  ```

- These files can then be referenced in your workflow using a "Load Image" (or similar) node pointing to the filename (e.g.,`my_static_image.png`).

Once you have created your custom `Dockerfile`, refer to the [Deployment Guide](deployment.md#deploying-custom-setups) for instructions on how to build, push and deploy your custom image to RunPod.

### Complete Custom `Dockerfile` Example

```Dockerfile
# start from a clean base image (replace <version> with the desired release)
FROM runpod/worker-comfyui:5.1.0-base

# install custom nodes using comfy-cli
RUN comfy-node-install comfyui-kjnodes comfyui-ic-light comfyui_ipadapter_plus comfyui_essentials ComfyUI-Hangover-Nodes

# download models using comfy-cli
# the "--filename" is what you use in your ComfyUI workflow
RUN comfy model download --url https://huggingface.co/KamCastle/jugg/resolve/main/juggernaut_reborn.safetensors --relative-path models/checkpoints --filename juggernaut_reborn.safetensors
RUN comfy model download --url https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus_sd15.bin --relative-path models/ipadapter --filename ip-adapter-plus_sd15.bin
RUN comfy model download --url https://huggingface.co/shiertier/clip_vision/resolve/main/SD15/model.safetensors --relative-path models/clip_vision --filename models.safetensors
RUN comfy model download --url https://huggingface.co/lllyasviel/ic-light/resolve/main/iclight_sd15_fcon.safetensors --relative-path models/diffusion_models --filename iclight_sd15_fcon.safetensors

# Copy local static input files into the ComfyUI input directory (delete if not needed)
# Assumes you have an 'input' folder next to your Dockerfile
COPY input/ /comfyui/input/
```

## Method 2: Network Volume

Using a Network Volume is primarily useful if you want to manage **models** separately from your worker image, especially if they are large or change often.

1.  **Create a Network Volume**:
    - Follow the [RunPod Network Volumes guide](https://docs.runpod.io/pods/storage/create-network-volumes) to create a volume in the same region as your endpoint.
2.  **Populate the Volume with Models**:
    - Use one of the methods described in the RunPod guide (e.g., temporary Pod + `wget`, direct upload) to place your model files into the correct ComfyUI directory structure **within the volume**. The root of the volume corresponds to `/workspace` inside the container.
      ```bash
      # Example structure inside the Network Volume:
      # /models/checkpoints/your_model.safetensors
      # /models/loras/your_lora.pt
      # /models/vae/your_vae.safetensors
      ```
    - **Important:** Ensure models are placed in the correct subdirectories (e.g., checkpoints in `models/checkpoints`, LoRAs in `models/loras`).
3.  **Configure Your Endpoint**:
    - Use the Network Volume in your endpoint configuration:
      - Either create a new endpoint or update an existing one (see [Deployment Guide](deployment.md)).
      - In the endpoint configuration, under `Advanced > Select Network Volume`, select your Network Volume.

**Note:**

- When a Network Volume is correctly attached, ComfyUI running inside the worker container will automatically detect and load models from the standard directories (`/workspace/models/...`) within that volume.
- This method is **not suitable for installing custom nodes**; use the Custom Dockerfile method for that.
