# Deployment

This guide explains how to deploy the `worker-comfyui` as a serverless endpoint on RunPod, covering both pre-built official images and custom-built images.

## Deploying Pre-Built Official Images

This is the simplest method if the official images meet your needs.

### Create your template (optional)

- Create a [new template](https://runpod.io/console/serverless/user/templates) by clicking on `New Template`
- In the dialog, configure:
  - Template Name: `worker-comfyui` (or your preferred name)
  - Template Type: serverless (change template type to "serverless")
  - Container Image: Use one of the official tags, e.g., `runpod/worker-comfyui:<version>-sd3`. (Refer to the main [README.md](../README.md#available-docker-images) for available image tags and the current version).
  - Container Registry Credentials: Leave as default (images are public).
  - Container Disk: Adjust based on the chosen image tag, see [GPU Recommendations](#gpu-recommendations).
  - (optional) Environment Variables: Configure S3 or other settings (see [Configuration Guide](configuration.md)).
    - Note: If you don't configure S3, images are returned as base64. For persistent storage across jobs without S3, consider using a [Network Volume](customization.md#method-2-network-volume-alternative-for-models).
- Click on `Save Template`

### Create your endpoint

- Navigate to [`Serverless > Endpoints`](https://www.runpod.io/console/serverless/user/endpoints) and click on `New Endpoint`
- In the dialog, configure:

  - Endpoint Name: `comfy` (or your preferred name)
  - Worker configuration: Select a GPU that can run the model included in your chosen image (see [GPU recommendations](#gpu-recommendations)).
  - Active Workers: `0` (Scale as needed based on expected load).
  - Max Workers: `3` (Set a limit based on your budget and scaling needs).
  - GPUs/Worker: `1`
  - Idle Timeout: `5` (Default is usually fine, adjust if needed).
  - Flash Boot: `enabled` (Recommended for faster worker startup).
  - Select Template: `worker-comfyui` (or the name you gave your template).
  - (optional) Advanced: If you are using a Network Volume, select it under `Select Network Volume`. See the [Customization Guide](customization.md#method-2-network-volume-alternative-for-models).

- Click `deploy`
- Your endpoint will be created. You can click on it to view the dashboard and find its ID.

### GPU recommendations (for Official Images)

| Model                     | Image Tag Suffix | Minimum VRAM Required | Recommended Container Size |
| ------------------------- | ---------------- | --------------------- | -------------------------- |
| Stable Diffusion XL       | `sdxl`           | 8 GB                  | 15 GB                      |
| Stable Diffusion 3 Medium | `sd3`            | 5 GB                  | 20 GB                      |
| FLUX.1 Schnell            | `flux1-schnell`  | 24 GB                 | 30 GB                      |
| FLUX.1 dev                | `flux1-dev`      | 24 GB                 | 30 GB                      |
| Base (No models)          | `base`           | N/A                   | 5 GB                       |

_Note: Container sizes are approximate and might vary slightly. Custom images will vary based on included models/nodes._

## Deploying Custom Setups

If you have created a custom environment using the methods in the [Customization Guide](customization.md), here's how to deploy it.

### Method 1: Manual Build, Push, and Deploy

This method involves building your custom Docker image locally, pushing it to a registry, and then deploying that image on RunPod.

1.  **Write your Dockerfile:** Follow the instructions in the [Customization Guide](customization.md#method-1-custom-dockerfile-recommended) to create your `Dockerfile` specifying the base image, nodes, models, and any static files.
2.  **Build the Docker image:** Navigate to the directory containing your `Dockerfile` and run:
    ```bash
    # Replace <your-image-name>:<tag> with your desired name and tag
    docker build --platform linux/amd64 -t <your-image-name>:<tag> .
    ```
    - **Crucially**, always include `--platform linux/amd64` for RunPod compatibility.
3.  **Tag the image for your registry:** Replace `<your-registry-username>` and `<your-image-name>:<tag>` accordingly.
    ```bash
    # Example for Docker Hub:
    docker tag <your-image-name>:<tag> <your-registry-username>/<your-image-name>:<tag>
    ```
4.  **Log in to your container registry:**
    ```bash
    # Example for Docker Hub:
    docker login
    ```
5.  **Push the image:**
    ```bash
    # Example for Docker Hub:
    docker push <your-registry-username>/<your-image-name>:<tag>
    ```
6.  **Deploy on RunPod:**
    - Follow the steps in [Create your template](#create-your-template-optional) above, but for the `Container Image` field, enter the full name of the image you just pushed (e.g., `<your-registry-username>/<your-image-name>:<tag>`).
    - If your registry is private, you will need to provide [Container Registry Credentials](https://docs.runpod.io/serverless/templates#container-registry-credentials).
    - Adjust the `Container Disk` size based on your custom image contents.
    - Follow the steps in [Create your endpoint](#create-your-endpoint) using the template you just created.

### Method 2: Deploying via RunPod GitHub Integration

RunPod offers a seamless way to deploy directly from your GitHub repository containing the `Dockerfile`. RunPod handles the build and deployment.

1.  **Prepare your GitHub Repository:** Ensure your repository contains the custom `Dockerfile` (as described in the [Customization Guide](customization.md#method-1-custom-dockerfile-recommended)) at the root or a specified path.
2.  **Connect GitHub to RunPod:** Authorize RunPod to access your repository via your RunPod account settings or when creating a new endpoint.
3.  **Create a New Serverless Endpoint:** In RunPod, navigate to Serverless -> `+ New Endpoint` and select the **"Start from GitHub Repo"** option.
4.  **Configure:**
    - Select the GitHub repository and branch you want to deploy (e.g., `main`).
    - Specify the **Context Path** (usually `/` if the Dockerfile is at the root).
    - Specify the **Dockerfile Path** (usually `Dockerfile`).
    - Configure your desired compute resources (GPU type, workers, etc.).
    - Configure any necessary [Environment Variables](configuration.md).
5.  **Deploy:** RunPod will clone the repository, build the image from your specified branch and Dockerfile, push it to a temporary registry, and deploy the endpoint.

Every `git push` to the configured branch will automatically trigger a new build and update your RunPod endpoint. For more details, refer to the [RunPod GitHub Integration Documentation](https://docs.runpod.io/serverless/github-integration).
