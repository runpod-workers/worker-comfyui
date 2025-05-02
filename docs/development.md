# Development and Local Testing

This guide covers setting up your local environment for developing and testing the `worker-comfyui`.

Both tests will use the data from [`test_input.json`](../test_input.json), so make your changes in there to test different workflow inputs properly.

## Setup

### Prerequisites

1.  Python >= 3.10
2.  `pip` (Python package installer)
3.  Virtual environment tool (like `venv`)

### Steps

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone https://github.com/runpod-workers/worker-comfyui.git
    cd worker-comfyui
    ```
2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    ```
3.  **Activate the virtual environment**:
    - **Windows (Command Prompt/PowerShell)**:
      ```bash
      .\.venv\Scripts\activate
      ```
    - **macOS / Linux (Bash/Zsh)**:
      ```bash
      source ./.venv/bin/activate
      ```
4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Setup for Windows (using WSL2)

Running Docker with GPU acceleration on Windows typically requires WSL2 (Windows Subsystem for Linux).

1.  **Install WSL2 and a Linux distribution** (like Ubuntu) following [Microsoft's official guide](https://learn.microsoft.com/en-us/windows/wsl/install). You generally don't need the GUI support for this.
2.  **Open your Linux distribution's terminal** (e.g., open Ubuntu from the Start menu or type `wsl` in Command Prompt/PowerShell).
3.  **Update packages** inside WSL:
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```
4.  **Install Docker Engine in WSL**:
    - Follow the [official Docker installation guide for your chosen Linux distribution](https://docs.docker.com/engine/install/#server) (e.g., Ubuntu).
    - **Important:** Add your user to the `docker` group to avoid using `sudo` for every Docker command: `sudo usermod -aG docker $USER`. You might need to close and reopen the terminal for this to take effect.
5.  **Install Docker Compose** (if not included with Docker Engine):
    ```bash
    sudo apt-get update
    sudo apt-get install docker-compose-plugin # Or use the standalone binary method if preferred
    ```
6.  **Install NVIDIA Container Toolkit in WSL**:
    - Follow the [NVIDIA Container Toolkit installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), ensuring you select the correct steps for your Linux distribution running inside WSL.
    - Configure Docker to use the NVIDIA runtime as default if desired, or specify it when running containers.
7.  **Enable GPU Acceleration in WSL**:
    - Ensure you have the latest NVIDIA drivers installed on your Windows host machine.
    - Follow the [NVIDIA guide for CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

After completing these steps, you should be able to run Docker commands, including `docker-compose`, from within your WSL terminal with GPU access.

> [!NOTE]
>
> - It is generally recommended to run the Docker commands (`docker build`, `docker-compose up`) from within the WSL environment terminal for consistency with the Linux-based container environment.
> - Accessing `localhost` URLs (like the local API or ComfyUI) from your Windows browser while the service runs inside WSL usually works, but network configurations can sometimes cause issues.

## Testing the RunPod Handler

Unit tests are provided to verify the core logic of the `handler.py`.

- **Run all tests**:
  ```bash
  python -m unittest discover tests/
  ```
- **Run a specific test file**:
  ```bash
  python -m unittest tests.test_handler
  ```
- **Run a specific test case or method**:

  ```bash
  # Example: Run all tests in the TestRunpodWorkerComfy class
  python -m unittest tests.test_handler.TestRunpodWorkerComfy

  # Example: Run a single test method
  python -m unittest tests.test_handler.TestRunpodWorkerComfy.test_s3_upload
  ```

## Local API Simulation (using Docker Compose)

For enhanced local development and end-to-end testing, you can start a local environment using Docker Compose that includes the worker and a ComfyUI instance.

> [!IMPORTANT]
>
> - This currently requires an **NVIDIA GPU** and correctly configured drivers + NVIDIA Container Toolkit (see Windows setup above if applicable).
> - Ensure Docker is running.

**Steps:**

1.  **Set Environment Variable (Optional but Recommended):**
    - While the `docker-compose.yml` sets `SERVE_API_LOCALLY=true` by default, you might manage environment variables externally (e.g., via a `.env` file).
    - Ensure the `SERVE_API_LOCALLY` environment variable is set to `true` for the `worker` service if you modify the compose file or use an `.env` file.
2.  **Start the services**:
    ```bash
    # From the project root directory
    docker-compose up --build
    ```
    - The `--build` flag ensures the image is built locally using the current state of the code and `Dockerfile`.
    - This will start two containers: `comfyui` and `worker`.

### Access the Local Worker API

- With the Docker Compose stack running, the worker's simulated RunPod API is accessible at: [http://localhost:8000](http://localhost:8000)
- You can send POST requests to `http://localhost:8000/run` or `http://localhost:8000/runsync` with the same JSON payload structure expected by the RunPod endpoint.
- Opening [http://localhost:8000/docs](http://localhost:8000/docs) in your browser will show the FastAPI auto-generated documentation (Swagger UI), allowing you to interact with the API directly.

### Access Local ComfyUI

- The underlying ComfyUI instance running in the `comfyui` container is accessible directly at: [http://localhost:8188](http://localhost:8188)
- This is useful for debugging workflows or observing the ComfyUI state while testing the worker.

### Stopping the Local Environment

- Press `Ctrl+C` in the terminal where `docker-compose up` is running.
- To ensure containers are removed, you can run: `docker-compose down`
