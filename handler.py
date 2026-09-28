import runpod
from runpod.serverless.utils import rp_upload
import json
import urllib.request
import urllib.parse
import time
import os
import requests
import base64
from io import BytesIO
import websocket
import uuid
import tempfile
import socket
import traceback
import logging

from network_volume import (
    is_network_volume_debug_enabled,
    run_network_volume_diagnostics,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = int(
    os.environ.get("COMFY_API_AVAILABLE_INTERVAL_MS", 50)
)
# Maximum number of API check attempts (0 = no limit, poll while ComfyUI process is alive)
COMFY_API_AVAILABLE_MAX_RETRIES = int(
    os.environ.get("COMFY_API_AVAILABLE_MAX_RETRIES", 0)
)
# Fallback retry limit when PID file is unavailable and retries=0
COMFY_API_FALLBACK_MAX_RETRIES = 500
# PID file written by start.sh so we can detect if ComfyUI has crashed
COMFY_PID_FILE = "/tmp/comfyui.pid"
# Websocket reconnection behaviour (can be overridden through environment variables)
# NOTE: more attempts and diagnostics improve debuggability whenever ComfyUI crashes mid-job.
#   • WEBSOCKET_RECONNECT_ATTEMPTS sets how many times we will try to reconnect.
#   • WEBSOCKET_RECONNECT_DELAY_S sets the sleep in seconds between attempts.
#
# If the respective env-vars are not supplied we fall back to sensible defaults ("5" and "3").
WEBSOCKET_RECONNECT_ATTEMPTS = int(os.environ.get("WEBSOCKET_RECONNECT_ATTEMPTS", 5))
WEBSOCKET_RECONNECT_DELAY_S = int(os.environ.get("WEBSOCKET_RECONNECT_DELAY_S", 3))

# Extra verbose websocket trace logs (set WEBSOCKET_TRACE=true to enable)
if os.environ.get("WEBSOCKET_TRACE", "false").lower() == "true":
    # This prints low-level frame information to stdout which is invaluable for diagnosing
    # protocol errors but can be noisy in production – therefore gated behind an env-var.
    websocket.enableTrace(True)

# Host where ComfyUI is running
COMFY_HOST = "127.0.0.1:8188"
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Model loader nodes — used for pre-flight validation of workflow model refs
# ---------------------------------------------------------------------------
# Maps a loader node's class_type to the model type it loads and the input
# field(s) that name a model file. The node → directory mapping is ComfyUI
# domain knowledge (documented in AGENTS.md), not discoverable from code.
MODEL_LOADER_NODES = {
    "CheckpointLoaderSimple": ("checkpoints", ("ckpt_name",)),
    "LoraLoader": ("loras", ("lora_name",)),
    "VAELoader": ("vae", ("vae_name",)),
    "DualCLIPLoader": ("text_encoders", ("clip_name1", "clip_name2")),
    "TripleCLIPLoader": ("text_encoders", ("clip_name1", "clip_name2", "clip_name3")),
    "UNETLoader": ("diffusion_models", ("unet_name",)),
    "UnetLoaderGGUF": ("diffusion_models", ("unet_name",)),
    "Hy3DModelLoader": ("diffusion_models", ("model",)),
    "UpscaleModelLoader": ("upscale_models", ("model_name",)),
}

# Where each model type lives on the network volume (see
# src/extra_model_paths.yaml — text encoders mount under clip/ and diffusion
# models under unet/, their legacy ComfyUI directory names).
MODEL_TYPE_VOLUME_DIRS = {
    "checkpoints": "/runpod-volume/models/checkpoints/",
    "loras": "/runpod-volume/models/loras/",
    "vae": "/runpod-volume/models/vae/",
    "text_encoders": "/runpod-volume/models/clip/",
    "diffusion_models": "/runpod-volume/models/unet/",
    "upscale_models": "/runpod-volume/models/upscale_models/",
}

# Placeholder some clients send when a UI model dropdown was never resolved
# to a real filename.
MODEL_LIST_PLACEHOLDER = "__list__"

# Cap how many available files an error message lists before truncating
MAX_LISTED_MODELS = 15

# ---------------------------------------------------------------------------
# Helper: quick reachability probe of ComfyUI HTTP endpoint (port 8188)
# ---------------------------------------------------------------------------


def _comfy_server_status():
    """Return a dictionary with basic reachability info for the ComfyUI HTTP server."""
    try:
        resp = requests.get(f"http://{COMFY_HOST}/", timeout=5)
        return {
            "reachable": resp.status_code == 200,
            "status_code": resp.status_code,
        }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _attempt_websocket_reconnect(ws_url, max_attempts, delay_s, initial_error):
    """
    Attempts to reconnect to the WebSocket server after a disconnect.

    Args:
        ws_url (str): The WebSocket URL (including client_id).
        max_attempts (int): Maximum number of reconnection attempts.
        delay_s (int): Delay in seconds between attempts.
        initial_error (Exception): The error that triggered the reconnect attempt.

    Returns:
        websocket.WebSocket: The newly connected WebSocket object.

    Raises:
        websocket.WebSocketConnectionClosedException: If reconnection fails after all attempts.
    """
    print(
        f"worker-comfyui - Websocket connection closed unexpectedly: {initial_error}. Attempting to reconnect..."
    )
    last_reconnect_error = initial_error
    for attempt in range(max_attempts):
        # Log current server status before each reconnect attempt so that we can
        # see whether ComfyUI is still alive (HTTP port 8188 responding) even if
        # the websocket dropped. This is extremely useful to differentiate
        # between a network glitch and an outright ComfyUI crash/OOM-kill.
        srv_status = _comfy_server_status()
        if not srv_status["reachable"]:
            # If ComfyUI itself is down there is no point in retrying the websocket –
            # bail out immediately so the caller gets a clear "ComfyUI crashed" error.
            print(
                f"worker-comfyui - ComfyUI HTTP unreachable – aborting websocket reconnect: {srv_status.get('error', 'status '+str(srv_status.get('status_code')))}"
            )
            raise websocket.WebSocketConnectionClosedException(
                "ComfyUI HTTP unreachable during websocket reconnect"
            )

        # Otherwise we proceed with reconnect attempts while server is up
        print(
            f"worker-comfyui - Reconnect attempt {attempt + 1}/{max_attempts}... (ComfyUI HTTP reachable, status {srv_status.get('status_code')})"
        )
        try:
            # Need to create a new socket object for reconnect
            new_ws = websocket.WebSocket()
            new_ws.connect(ws_url, timeout=10)  # Use existing ws_url
            print(f"worker-comfyui - Websocket reconnected successfully.")
            return new_ws  # Return the new connected socket
        except (
            websocket.WebSocketException,
            ConnectionRefusedError,
            socket.timeout,
            OSError,
        ) as reconn_err:
            last_reconnect_error = reconn_err
            print(
                f"worker-comfyui - Reconnect attempt {attempt + 1} failed: {reconn_err}"
            )
            if attempt < max_attempts - 1:
                print(
                    f"worker-comfyui - Waiting {delay_s} seconds before next attempt..."
                )
                time.sleep(delay_s)
            else:
                print(f"worker-comfyui - Max reconnection attempts reached.")

    # If loop completes without returning, raise an exception
    print("worker-comfyui - Failed to reconnect websocket after connection closed.")
    raise websocket.WebSocketConnectionClosedException(
        f"Connection closed and failed to reconnect. Last error: {last_reconnect_error}"
    )


def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Validate 'images' in input, if provided
    images = job_input.get("images")
    if images is not None:
        if not isinstance(images, list) or not all(
            "name" in image and "image" in image for image in images
        ):
            return (
                None,
                "'images' must be a list of objects with 'name' and 'image' keys",
            )

    # Optional: API key for Comfy.org API Nodes, passed per-request
    comfy_org_api_key = job_input.get("comfy_org_api_key")

    # Return validated data and no error
    return {
        "workflow": workflow,
        "images": images,
        "comfy_org_api_key": comfy_org_api_key,
    }, None


def _get_comfyui_pid():
    """Read the ComfyUI process PID from the PID file written by start.sh."""
    try:
        with open(COMFY_PID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_comfyui_process_alive():
    """Check whether the ComfyUI process is still running.

    Returns True if alive, False if dead, None if PID file not found.
    """
    pid = _get_comfyui_pid()
    if pid is None:
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but we can't signal it


def check_server(url, retries=0, delay=50):
    """
    Check if a server is reachable via HTTP GET request.

    When a PID file is available (written by start.sh), the function polls
    indefinitely while the ComfyUI process is alive and fails immediately
    when the process exits.  When no PID file is found it falls back to
    the retry limit for backward compatibility.

    Args:
        url (str): The URL to check.
        retries (int): Max attempts. 0 means unlimited (poll while process alive).
        delay (int): Time in milliseconds between retries.

    Returns:
        bool: True if the server is reachable, False otherwise.
    """
    print(f"worker-comfyui - Checking API server at {url}...")

    # Guard against zero/negative delay to avoid division by zero
    delay = max(1, delay)
    # How often to print a "still waiting" log (every ~10 seconds)
    log_every = max(1, int(10_000 / delay))
    attempt = 0

    while True:
        # --- Check if ComfyUI process is still alive ---
        process_status = _is_comfyui_process_alive()
        if process_status is False:
            print(
                "worker-comfyui - ComfyUI process has exited. "
                "Server will not become reachable."
            )
            return False

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"worker-comfyui - API is reachable")
                return True
        except requests.Timeout:
            pass
        except requests.RequestException:
            pass

        attempt += 1

        # If we can't track the process, enforce a retry limit to avoid
        # hanging forever when the PID file is never written
        fallback = retries if retries > 0 else COMFY_API_FALLBACK_MAX_RETRIES
        if process_status is None and attempt >= fallback:
            print(
                f"worker-comfyui - Failed to connect to server at {url} "
                f"after {fallback} attempts (no PID file found)."
            )
            return False

        if attempt % log_every == 0:
            elapsed_s = (attempt * delay) / 1000
            print(
                f"worker-comfyui - Still waiting for API server... "
                f"({elapsed_s:.0f}s elapsed, attempt {attempt})"
            )

        time.sleep(delay / 1000)


def upload_images(images):
    """
    Upload a list of base64 encoded images to the ComfyUI server using the /upload/image endpoint.

    Args:
        images (list): A list of dictionaries, each containing the 'name' of the image and the 'image' as a base64 encoded string.

    Returns:
        dict: A dictionary indicating success or error.
    """
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []

    print(f"worker-comfyui - Uploading {len(images)} image(s)...")

    for image in images:
        try:
            name = image["name"]
            image_data_uri = image["image"]  # Get the full string (might have prefix)

            # --- Strip Data URI prefix if present ---
            if "," in image_data_uri:
                # Find the comma and take everything after it
                base64_data = image_data_uri.split(",", 1)[1]
            else:
                # Assume it's already pure base64
                base64_data = image_data_uri
            # --- End strip ---

            blob = base64.b64decode(base64_data)  # Decode the cleaned data

            # Prepare the form data
            files = {
                "image": (name, BytesIO(blob), "image/png"),
                "overwrite": (None, "true"),
            }

            # POST request to upload the image
            response = requests.post(
                f"http://{COMFY_HOST}/upload/image", files=files, timeout=30
            )
            response.raise_for_status()

            responses.append(f"Successfully uploaded {name}")
            print(f"worker-comfyui - Successfully uploaded {name}")

        except base64.binascii.Error as e:
            error_msg = f"Error decoding base64 for {image.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except requests.Timeout:
            error_msg = f"Timeout uploading {image.get('name', 'unknown')}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except requests.RequestException as e:
            error_msg = f"Error uploading {image.get('name', 'unknown')}: {e}"
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)
        except Exception as e:
            error_msg = (
                f"Unexpected error uploading {image.get('name', 'unknown')}: {e}"
            )
            print(f"worker-comfyui - {error_msg}")
            upload_errors.append(error_msg)

    if upload_errors:
        print(f"worker-comfyui - image(s) upload finished with errors")
        return {
            "status": "error",
            "message": "Some images failed to upload",
            "details": upload_errors,
        }

    print(f"worker-comfyui - image(s) upload complete")
    return {
        "status": "success",
        "message": "All images uploaded successfully",
        "details": responses,
    }


def _fetch_object_info():
    """
    Fetch ComfyUI's /object_info (registered nodes and their input options).

    Returns:
        dict: The parsed /object_info payload, or None if it can't be fetched.
    """
    try:
        response = requests.get(f"http://{COMFY_HOST}/object_info", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"worker-comfyui - Warning: Could not fetch /object_info: {e}")
        return None


def _loader_field_options(object_info, class_type, field):
    """
    Return the list of valid options for a node input field, or None when the
    node/field is not registered or the field is not an option list.
    """
    node_info = object_info.get(class_type)
    if not isinstance(node_info, dict):
        return None
    inputs = node_info.get("input", {})
    if not isinstance(inputs, dict):
        return None
    for section in ("required", "optional"):
        section_inputs = inputs.get(section)
        if not isinstance(section_inputs, dict):
            continue
        spec = section_inputs.get(field)
        # Option-list inputs look like [["file_a", "file_b"], {...}]
        if (
            isinstance(spec, (list, tuple))
            and len(spec) > 0
            and isinstance(spec[0], list)
        ):
            return spec[0]
    return None


def get_available_models():
    """
    Get list of available models from ComfyUI, grouped by model type.

    Queries /object_info and extracts the option list of every known model
    loader node (see MODEL_LOADER_NODES), so the result covers checkpoints,
    loras, vae, text encoders, diffusion models and upscale models.

    Returns:
        dict: Mapping of model type (e.g. 'checkpoints') to a sorted list of
              available filenames. Empty dict if ComfyUI can't be reached.
    """
    object_info = _fetch_object_info()
    if object_info is None:
        return {}

    available_models = {}
    for class_type, (model_type, fields) in MODEL_LOADER_NODES.items():
        for field in fields:
            options = _loader_field_options(object_info, class_type, field)
            if options:
                available_models.setdefault(model_type, set()).update(options)
    return {model_type: sorted(files) for model_type, files in available_models.items()}


def _format_options(options):
    """Format an option list for an error message, truncating long lists."""
    shown = sorted(options)[:MAX_LISTED_MODELS]
    formatted = ", ".join(f"'{o}'" for o in shown)
    remaining = len(options) - len(shown)
    if remaining > 0:
        formatted += f" (and {remaining} more)"
    return formatted


def _check_model_reference(object_info, node_id, class_type, field, value, model_type):
    """
    Validate one model-name input of a loader node.

    Returns a problem description string, or None if the reference is fine
    (or cannot be judged from /object_info).
    """
    volume_dir = MODEL_TYPE_VOLUME_DIRS.get(
        model_type, f"/runpod-volume/models/{model_type}/"
    )

    if value == MODEL_LIST_PLACEHOLDER:
        available = _loader_field_options(object_info, class_type, field) or []
        msg = (
            f"Node {node_id} ({class_type}.{field}): got the placeholder "
            f"'{MODEL_LIST_PLACEHOLDER}' instead of a real model filename — the client "
            f"sent a UI default that was never replaced with an actual file. "
            f"Set it to one of the available {model_type} files"
        )
        if available:
            msg += f": {_format_options(available)}"
        return msg

    available = _loader_field_options(object_info, class_type, field)
    if available is None:
        # Node type or field not registered in this ComfyUI build — let
        # ComfyUI's own validation decide instead of guessing.
        return None
    if value in available:
        return None

    msg = (
        f"Node {node_id} ({class_type}.{field}): '{value}' not found in "
        f"{model_type}. Expected at {volume_dir}{value}"
    )
    # Matching mirrors ComfyUI's own validation and is case-sensitive; when a
    # file differs only in case, say so instead of just "not found".
    case_match = next((a for a in available if a.lower() == value.lower()), None)
    if case_match:
        msg += f". Did you mean '{case_match}'? (filenames are case-sensitive)"
    elif available:
        msg += f". Available {model_type}: {_format_options(available)}"
    else:
        msg += (
            f". No {model_type} files are available — check that your network "
            f"volume contains them under {volume_dir}"
        )
    return msg


def _check_image_reference(object_info, node_id, value):
    """
    Validate a LoadImage 'image' input against ComfyUI's known input images.

    Returns a problem description string, or None if the reference is fine.
    """
    if value == MODEL_LIST_PLACEHOLDER:
        return (
            f"Node {node_id} (LoadImage.image): got the placeholder "
            f"'{MODEL_LIST_PLACEHOLDER}' instead of a real image filename — the client "
            f"sent a UI default that was never replaced with an actual file"
        )
    available = _loader_field_options(object_info, "LoadImage", "image")
    if available is None or value in available:
        return None
    # ComfyUI accepts annotated names like "example.png [input]" that are not
    # part of the option list — don't second-guess those.
    if value.endswith("]") and " [" in value:
        return None
    return (
        f"Node {node_id} (LoadImage.image): '{value}' is not an available input "
        f"image. Upload it via the request's 'images' parameter or place it in "
        f"ComfyUI's input directory"
    )


def validate_workflow_models(workflow):
    """
    Pre-flight check that every model file referenced by the workflow exists.

    Walks the workflow graph and, for every known model loader node, verifies
    the referenced filename against what ComfyUI actually has registered
    (/object_info). This surfaces every missing model in one clear error
    *before* the workflow is submitted, instead of ComfyUI's cryptic
    'Value not in list' validation crash after the cold start.

    If /object_info can't be fetched, validation is skipped (fail open): a
    transient error must not block a valid workflow, and queue_workflow's
    400 handling remains as the backstop.

    Args:
        workflow (dict): The workflow graph ({node_id: {class_type, inputs}}).

    Returns:
        str: A user-facing error message listing every problem found, or None
             if the workflow looks valid (or validation was skipped).
    """
    if not isinstance(workflow, dict):
        return None

    object_info = _fetch_object_info()
    if object_info is None:
        print(
            "worker-comfyui - Skipping workflow model pre-flight check "
            "(could not fetch /object_info)"
        )
        return None

    problems = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type")
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        if class_type in MODEL_LOADER_NODES:
            model_type, fields = MODEL_LOADER_NODES[class_type]
            for field in fields:
                value = inputs.get(field)
                # Non-string values are links to other nodes' outputs
                # ([node_id, slot]) — nothing to check.
                if not isinstance(value, str):
                    continue
                problem = _check_model_reference(
                    object_info, node_id, class_type, field, value, model_type
                )
                if problem:
                    problems.append(problem)
        elif class_type == "LoadImage":
            value = inputs.get("image")
            if isinstance(value, str):
                problem = _check_image_reference(object_info, node_id, value)
                if problem:
                    problems.append(problem)

    if not problems:
        return None

    message = (
        "Workflow validation failed — the following referenced files are not "
        "available on this worker:\n"
    )
    message += "\n".join(f"• {problem}" for problem in problems)
    message += (
        "\n\nUpload the missing file(s) to the matching directory on your "
        "network volume, or update the workflow to use one of the available files."
    )
    return message


def queue_workflow(workflow, client_id, comfy_org_api_key=None):
    """
    Queue a workflow to be processed by ComfyUI

    Args:
        workflow (dict): A dictionary containing the workflow to be processed
        client_id (str): The client ID for the websocket connection
        comfy_org_api_key (str, optional): Comfy.org API key for API Nodes

    Returns:
        dict: The JSON response from ComfyUI after processing the workflow

    Raises:
        ValueError: If the workflow validation fails with detailed error information
    """
    # Include client_id in the prompt payload
    payload = {"prompt": workflow, "client_id": client_id}

    # Optionally inject Comfy.org API key for API Nodes.
    # Precedence: per-request key (argument) overrides environment variable.
    # Note: We use our consistent naming (comfy_org_api_key) but transform to
    # ComfyUI's expected format (api_key_comfy_org) when sending.
    key_from_env = os.environ.get("COMFY_ORG_API_KEY")
    effective_key = comfy_org_api_key if comfy_org_api_key else key_from_env
    if effective_key:
        payload["extra_data"] = {"api_key_comfy_org": effective_key}
    data = json.dumps(payload).encode("utf-8")

    # Use requests for consistency and timeout
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        f"http://{COMFY_HOST}/prompt", data=data, headers=headers, timeout=30
    )

    # Handle validation errors with detailed information
    if response.status_code == 400:
        print(f"worker-comfyui - ComfyUI returned 400. Response body: {response.text}")
        try:
            error_data = response.json()
            print(f"worker-comfyui - Parsed error data: {error_data}")

            # Try to extract meaningful error information
            error_message = "Workflow validation failed"
            error_details = []

            # ComfyUI seems to return different error formats, let's handle them all
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    error_message = error_info.get("message", error_message)
                    if error_info.get("type") == "prompt_outputs_failed_validation":
                        error_message = "Workflow validation failed"
                else:
                    error_message = str(error_info)

            # Check for node validation errors in the response
            if "node_errors" in error_data:
                for node_id, node_error in error_data["node_errors"].items():
                    if isinstance(node_error, dict):
                        for error_type, error_msg in node_error.items():
                            error_details.append(
                                f"Node {node_id} ({error_type}): {error_msg}"
                            )
                    else:
                        error_details.append(f"Node {node_id}: {node_error}")

            # Check if the error data itself contains validation info
            if error_data.get("type") == "prompt_outputs_failed_validation":
                error_message = error_data.get("message", "Workflow validation failed")
                # For this type of error, we need to parse the validation details from logs
                # Since ComfyUI doesn't seem to include detailed validation errors in the response
                # Let's provide a more helpful generic message
                available_models = get_available_models()
                if available_models.get("checkpoints"):
                    error_message += f"\n\nThis usually means a required model or parameter is not available."
                    error_message += f"\nAvailable checkpoint models: {', '.join(available_models['checkpoints'])}"
                else:
                    error_message += "\n\nThis usually means a required model or parameter is not available."
                    error_message += "\nNo checkpoint models appear to be available. Please check your model installation."

                raise ValueError(error_message)

            # If we have specific validation errors, format them nicely
            if error_details:
                detailed_message = f"{error_message}:\n" + "\n".join(
                    f"• {detail}" for detail in error_details
                )

                # Try to provide helpful suggestions for common errors
                if any(
                    "not in list" in detail and "ckpt_name" in detail
                    for detail in error_details
                ):
                    available_models = get_available_models()
                    if available_models.get("checkpoints"):
                        detailed_message += f"\n\nAvailable checkpoint models: {', '.join(available_models['checkpoints'])}"
                    else:
                        detailed_message += "\n\nNo checkpoint models appear to be available. Please check your model installation."

                raise ValueError(detailed_message)
            else:
                # Fallback to the raw response if we can't parse specific errors
                raise ValueError(f"{error_message}. Raw response: {response.text}")

        except (json.JSONDecodeError, KeyError) as e:
            # If we can't parse the error response, fall back to the raw text
            raise ValueError(
                f"ComfyUI validation failed (could not parse error response): {response.text}"
            )

    # For other HTTP errors, raise them normally
    response.raise_for_status()
    return response.json()


def get_history(prompt_id):
    """
    Retrieve the history of a given prompt using its ID

    Args:
        prompt_id (str): The ID of the prompt whose history is to be retrieved

    Returns:
        dict: The history of the prompt, containing all the processing steps and results
    """
    # Use requests for consistency and timeout
    response = requests.get(f"http://{COMFY_HOST}/history/{prompt_id}", timeout=30)
    response.raise_for_status()
    return response.json()


def get_image_data(filename, subfolder, image_type):
    """
    Fetch image bytes from the ComfyUI /view endpoint.

    Args:
        filename (str): The filename of the image.
        subfolder (str): The subfolder where the image is stored.
        image_type (str): The type of the image (e.g., 'output').

    Returns:
        bytes: The raw image data, or None if an error occurs.
    """
    print(
        f"worker-comfyui - Fetching image data: type={image_type}, subfolder={subfolder}, filename={filename}"
    )
    data = {"filename": filename, "subfolder": subfolder, "type": image_type}
    url_values = urllib.parse.urlencode(data)
    try:
        # Use requests for consistency and timeout
        response = requests.get(f"http://{COMFY_HOST}/view?{url_values}", timeout=60)
        response.raise_for_status()
        print(f"worker-comfyui - Successfully fetched image data for {filename}")
        return response.content
    except requests.Timeout:
        print(f"worker-comfyui - Timeout fetching image data for {filename}")
        return None
    except requests.RequestException as e:
        print(f"worker-comfyui - Error fetching image data for {filename}: {e}")
        return None
    except Exception as e:
        print(
            f"worker-comfyui - Unexpected error fetching image data for {filename}: {e}"
        )
        return None


def handler(job):
    """
    Handles a job using ComfyUI via websockets for status and image retrieval.

    Args:
        job (dict): A dictionary containing job details and input parameters.

    Returns:
        dict: A dictionary containing either an error message or a success status with generated images.
    """
    # ---------------------------------------------------------------------------
    # Network Volume Diagnostics (opt-in via NETWORK_VOLUME_DEBUG=true)
    # ---------------------------------------------------------------------------
    if is_network_volume_debug_enabled():
        run_network_volume_diagnostics()

    job_input = job["input"]
    job_id = job["id"]

    # Make sure that the input is valid
    validated_data, error_message = validate_input(job_input)
    if error_message:
        return {"error": error_message}

    # Extract validated data
    workflow = validated_data["workflow"]
    input_images = validated_data.get("images")

    # Make sure that the ComfyUI HTTP API is available before proceeding
    if not check_server(
        f"http://{COMFY_HOST}/",
        COMFY_API_AVAILABLE_MAX_RETRIES,
        COMFY_API_AVAILABLE_INTERVAL_MS,
    ):
        return {
            "error": f"ComfyUI server ({COMFY_HOST}) not reachable after multiple retries."
        }

    # Upload input images if they exist
    if input_images:
        upload_result = upload_images(input_images)
        if upload_result["status"] == "error":
            # Return upload errors
            return {
                "error": "Failed to upload one or more input images",
                "details": upload_result["details"],
            }

    # Pre-flight: verify every model file the workflow references actually
    # exists before submitting, so a missing model fails fast with a clear
    # message instead of ComfyUI's raw validation crash. Runs after image
    # upload so freshly uploaded LoadImage inputs are already visible.
    preflight_error = validate_workflow_models(workflow)
    if preflight_error:
        print(f"worker-comfyui - Workflow model pre-flight failed:\n{preflight_error}")
        return {"error": preflight_error}

    ws = None
    client_id = str(uuid.uuid4())
    prompt_id = None
    output_data = []
    errors = []

    try:
        # Establish WebSocket connection
        ws_url = f"ws://{COMFY_HOST}/ws?clientId={client_id}"
        print(f"worker-comfyui - Connecting to websocket: {ws_url}")
        ws = websocket.WebSocket()
        ws.connect(ws_url, timeout=10)
        print(f"worker-comfyui - Websocket connected")

        # Queue the workflow
        try:
            # Pass per-request API key if provided in input
            queued_workflow = queue_workflow(
                workflow,
                client_id,
                comfy_org_api_key=validated_data.get("comfy_org_api_key"),
            )
            prompt_id = queued_workflow.get("prompt_id")
            if not prompt_id:
                raise ValueError(
                    f"Missing 'prompt_id' in queue response: {queued_workflow}"
                )
            print(f"worker-comfyui - Queued workflow with ID: {prompt_id}")
        except requests.RequestException as e:
            print(f"worker-comfyui - Error queuing workflow: {e}")
            raise ValueError(f"Error queuing workflow: {e}")
        except Exception as e:
            print(f"worker-comfyui - Unexpected error queuing workflow: {e}")
            # For ValueError exceptions from queue_workflow, pass through the original message
            if isinstance(e, ValueError):
                raise e
            else:
                raise ValueError(f"Unexpected error queuing workflow: {e}")

        # Wait for execution completion via WebSocket
        print(f"worker-comfyui - Waiting for workflow execution ({prompt_id})...")
        execution_done = False
        while True:
            try:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message.get("type") == "status":
                        status_data = message.get("data", {}).get("status", {})
                        print(
                            f"worker-comfyui - Status update: {status_data.get('exec_info', {}).get('queue_remaining', 'N/A')} items remaining in queue"
                        )
                    elif message.get("type") == "executing":
                        data = message.get("data", {})
                        if (
                            data.get("node") is None
                            and data.get("prompt_id") == prompt_id
                        ):
                            print(
                                f"worker-comfyui - Execution finished for prompt {prompt_id}"
                            )
                            execution_done = True
                            break
                    elif message.get("type") == "execution_error":
                        data = message.get("data", {})
                        if data.get("prompt_id") == prompt_id:
                            error_details = f"Node Type: {data.get('node_type')}, Node ID: {data.get('node_id')}, Message: {data.get('exception_message')}"
                            print(
                                f"worker-comfyui - Execution error received: {error_details}"
                            )
                            errors.append(f"Workflow execution error: {error_details}")
                            break
                else:
                    continue
            except websocket.WebSocketTimeoutException:
                print(f"worker-comfyui - Websocket receive timed out. Still waiting...")
                continue
            except websocket.WebSocketConnectionClosedException as closed_err:
                try:
                    # Attempt to reconnect
                    ws = _attempt_websocket_reconnect(
                        ws_url,
                        WEBSOCKET_RECONNECT_ATTEMPTS,
                        WEBSOCKET_RECONNECT_DELAY_S,
                        closed_err,
                    )

                    print(
                        "worker-comfyui - Resuming message listening after successful reconnect."
                    )
                    continue
                except (
                    websocket.WebSocketConnectionClosedException
                ) as reconn_failed_err:
                    # If _attempt_websocket_reconnect fails, it raises this exception
                    # Let this exception propagate to the outer handler's except block
                    raise reconn_failed_err

            except json.JSONDecodeError:
                print(f"worker-comfyui - Received invalid JSON message via websocket.")

        if not execution_done and not errors:
            raise ValueError(
                "Workflow monitoring loop exited without confirmation of completion or error."
            )

        # Fetch history even if there were execution errors, some outputs might exist
        print(f"worker-comfyui - Fetching history for prompt {prompt_id}...")
        history = get_history(prompt_id)

        if prompt_id not in history:
            error_msg = f"Prompt ID {prompt_id} not found in history after execution."
            print(f"worker-comfyui - {error_msg}")
            if not errors:
                return {"error": error_msg}
            else:
                errors.append(error_msg)
                return {
                    "error": "Job processing failed, prompt ID not found in history.",
                    "details": errors,
                }

        prompt_history = history.get(prompt_id, {})
        outputs = prompt_history.get("outputs", {})

        if not outputs:
            warning_msg = f"No outputs found in history for prompt {prompt_id}."
            print(f"worker-comfyui - {warning_msg}")
            if not errors:
                errors.append(warning_msg)

        print(f"worker-comfyui - Processing {len(outputs)} output nodes...")
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                print(
                    f"worker-comfyui - Node {node_id} contains {len(node_output['images'])} image(s)"
                )
                for image_info in node_output["images"]:
                    filename = image_info.get("filename")
                    subfolder = image_info.get("subfolder", "")
                    img_type = image_info.get("type")

                    # skip temp images
                    if img_type == "temp":
                        print(
                            f"worker-comfyui - Skipping image {filename} because type is 'temp'"
                        )
                        continue

                    if not filename:
                        warn_msg = f"Skipping image in node {node_id} due to missing filename: {image_info}"
                        print(f"worker-comfyui - {warn_msg}")
                        errors.append(warn_msg)
                        continue

                    image_bytes = get_image_data(filename, subfolder, img_type)

                    if image_bytes:
                        file_extension = os.path.splitext(filename)[1] or ".png"

                        if os.environ.get("BUCKET_ENDPOINT_URL"):
                            try:
                                with tempfile.NamedTemporaryFile(
                                    suffix=file_extension, delete=False
                                ) as temp_file:
                                    temp_file.write(image_bytes)
                                    temp_file_path = temp_file.name
                                print(
                                    f"worker-comfyui - Wrote image bytes to temporary file: {temp_file_path}"
                                )

                                print(f"worker-comfyui - Uploading {filename} to S3...")
                                # Use BUCKET_PREFIX if set, otherwise use original upload_image for backward compatibility
                                bucket_prefix = os.environ.get("BUCKET_PREFIX", "").strip("/")
                                if bucket_prefix:
                                    s3_prefix = f"{bucket_prefix}/{job_id}"
                                    s3_url = rp_upload.upload_file_to_bucket(
                                        file_name=filename,
                                        file_location=temp_file_path,
                                        prefix=s3_prefix,
                                    )
                                else:
                                    s3_url = rp_upload.upload_image(job_id, temp_file_path)
                                os.remove(temp_file_path)  # Clean up temp file
                                print(
                                    f"worker-comfyui - Uploaded {filename} to S3: {s3_url}"
                                )
                                # Append dictionary with filename and URL
                                output_data.append(
                                    {
                                        "filename": filename,
                                        "type": "s3_url",
                                        "data": s3_url,
                                    }
                                )
                            except Exception as e:
                                error_msg = f"Error uploading {filename} to S3: {e}"
                                print(f"worker-comfyui - {error_msg}")
                                errors.append(error_msg)
                                if "temp_file_path" in locals() and os.path.exists(
                                    temp_file_path
                                ):
                                    try:
                                        os.remove(temp_file_path)
                                    except OSError as rm_err:
                                        print(
                                            f"worker-comfyui - Error removing temp file {temp_file_path}: {rm_err}"
                                        )
                        else:
                            # Return as base64 string
                            try:
                                base64_image = base64.b64encode(image_bytes).decode(
                                    "utf-8"
                                )
                                # Append dictionary with filename and base64 data
                                output_data.append(
                                    {
                                        "filename": filename,
                                        "type": "base64",
                                        "data": base64_image,
                                    }
                                )
                                print(f"worker-comfyui - Encoded {filename} as base64")
                            except Exception as e:
                                error_msg = f"Error encoding {filename} to base64: {e}"
                                print(f"worker-comfyui - {error_msg}")
                                errors.append(error_msg)
                    else:
                        error_msg = f"Failed to fetch image data for {filename} from /view endpoint."
                        errors.append(error_msg)

            # Check for other output types
            other_keys = [k for k in node_output.keys() if k != "images"]
            if other_keys:
                warn_msg = (
                    f"Node {node_id} produced unhandled output keys: {other_keys}."
                )
                print(f"worker-comfyui - WARNING: {warn_msg}")
                print(
                    f"worker-comfyui - --> If this output is useful, please consider opening an issue on GitHub to discuss adding support."
                )

    except websocket.WebSocketException as e:
        print(f"worker-comfyui - WebSocket Error: {e}")
        print(traceback.format_exc())
        return {"error": f"WebSocket communication error: {e}"}
    except requests.RequestException as e:
        print(f"worker-comfyui - HTTP Request Error: {e}")
        print(traceback.format_exc())
        return {"error": f"HTTP communication error with ComfyUI: {e}"}
    except ValueError as e:
        print(f"worker-comfyui - Value Error: {e}")
        print(traceback.format_exc())
        return {"error": str(e)}
    except Exception as e:
        print(f"worker-comfyui - Unexpected Handler Error: {e}")
        print(traceback.format_exc())
        return {"error": f"An unexpected error occurred: {e}"}
    finally:
        if ws and ws.connected:
            print(f"worker-comfyui - Closing websocket connection.")
            ws.close()

    final_result = {}

    if output_data:
        final_result["images"] = output_data

    if errors:
        final_result["errors"] = errors
        print(f"worker-comfyui - Job completed with errors/warnings: {errors}")

    if not output_data and errors:
        print(f"worker-comfyui - Job failed with no output images.")
        return {
            "error": "Job processing failed",
            "details": errors,
        }
    elif not output_data and not errors:
        print(
            f"worker-comfyui - Job completed successfully, but the workflow produced no images."
        )
        final_result["status"] = "success_no_images"
        final_result["images"] = []

    print(f"worker-comfyui - Job completed. Returning {len(output_data)} image(s).")
    return final_result


if __name__ == "__main__":
    print("worker-comfyui - Starting handler...")
    runpod.serverless.start({"handler": handler})
