# Introduction

This project (`worker-comfyui`) provides a way to run [ComfyUI](https://github.com/comfyanonymous/ComfyUI) as a serverless API worker on the [RunPod](https://www.runpod.io/) platform. Its main purpose is to allow users to submit ComfyUI image generation workflows via a simple API call and receive the resulting images, either directly as base64-encoded strings or via an upload to an AWS S3 bucket.

It packages ComfyUI into Docker images, manages job handling via the `runpod` SDK, and facilitates configuration through environment variables.

# Project Conventions and Rules

This document outlines the key operational and structural conventions for the `worker-comfyui` project. While there are no strict code-style rules enforced by linters currently, following these conventions ensures consistency and smooth development/deployment.

## 1. Configuration

- **Environment Variables:** All external configurations (e.g., AWS S3 credentials, RunPod behavior modifications like `REFRESH_WORKER`, ComfyUI polling settings) **must** be managed via environment variables.
- Refer to the main `README.md` sections "Config" and "Upload image to AWS S3" for details on available variables.

## 2. Docker Usage

- **Container-Centric:** Development, testing, and deployment are heavily reliant on Docker.
- **Platform:** When building Docker images intended for RunPod, **always** use the `--platform linux/amd64` flag to ensure compatibility.
  ```bash
  # Example build command
  docker build --platform linux/amd64 -t my-image:tag .
  ```
- **Customization:** Follow the methods in the `README.md` for adding custom models/nodes (Network Volume or Dockerfile edits + snapshots).

## 3. API Interaction

- **Input Structure:** API calls to the `/run` or `/runsync` endpoints must adhere to the JSON structure specified in the `README.md` ("API specification"). The primary key is `input`, containing `workflow` (mandatory object) and `images` (optional array).
- **Image Encoding:** Input images provided in the `input.images` array must be base64 encoded strings.
- **Workflow Format:** The `input.workflow` object should contain the JSON exported from ComfyUI using the "Save (API Format)" option (requires enabling "Dev mode Options" in ComfyUI settings).

## 4. Testing

- **Unit Tests:** Automated tests are located in the `tests/` directory and should be run using `python -m unittest discover`. Add new tests for new functionality or bug fixes.
- **Local Environment:** Use `docker-compose up` for local end-to-end testing. This requires a correctly configured Docker environment with NVIDIA GPU support.

## 5. Dependencies

- **Python:** Manage Python dependencies using `pip` and the `requirements.txt` file. Keep this file up-to-date.

## 6. Code Style (General Guidance)

- While not enforced by tooling, aim for code clarity and consistency. Follow general Python best practices (e.g., PEP 8).
- Use meaningful variable and function names.
- Add comments where the logic is non-obvious.
