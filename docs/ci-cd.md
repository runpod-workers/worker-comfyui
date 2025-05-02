# CI/CD

This project includes GitHub Actions workflows to automatically build and deploy Docker images to Docker Hub.

## Automatic Deployment to Docker Hub with GitHub Actions

The repository contains two workflows located in the `.github/workflows` directory:

- [`dev.yml`](../.github/workflows/dev.yml): Creates the images (base, sdxl, sd3, flux variants) and pushes them to Docker Hub tagged as `<image_name>:dev` on every push to the `main` branch.
- [`release.yml`](../.github/workflows/release.yml): Creates the images and pushes them to Docker Hub tagged as `<image_name>:latest` and `<image_name>:<release_version>` (e.g., `worker-comfyui:3.7.0`). This workflow is triggered only when a new release is created on GitHub.

### Configuration for Your Fork

If you have forked this repository and want to use these actions to publish images to your own Docker Hub account, you need to configure the following in your GitHub repository settings:

1.  **Secrets** (`Settings > Secrets and variables > Actions > New repository secret`):

    | Secret Name                | Description                                                                | Example Value       |
    | -------------------------- | -------------------------------------------------------------------------- | ------------------- |
    | `DOCKERHUB_USERNAME`       | Your Docker Hub username.                                                  | `your-dockerhub-id` |
    | `DOCKERHUB_TOKEN`          | Your Docker Hub access token with read/write permissions.                  | `dckr_pat_...`      |
    | `HUGGINGFACE_ACCESS_TOKEN` | Your READ access token from Hugging Face (required only for building SD3). | `hf_...`            |

2.  **Variables** (`Settings > Secrets and variables > Actions > New repository variable`):

    | Variable Name    | Description                                                                  | Example Value              |
    | ---------------- | ---------------------------------------------------------------------------- | -------------------------- |
    | `DOCKERHUB_REPO` | The target repository (namespace) on Docker Hub where images will be pushed. | `your-dockerhub-id`        |
    | `DOCKERHUB_IMG`  | The base name for the image to be pushed to Docker Hub.                      | `my-custom-worker-comfyui` |

With these secrets and variables configured, the actions will push the built images (e.g., `your-dockerhub-id/my-custom-worker-comfyui:dev`, `your-dockerhub-id/my-custom-worker-comfyui:1.0.0`, `your-dockerhub-id/my-custom-worker-comfyui:latest`) to your Docker Hub account when triggered.
