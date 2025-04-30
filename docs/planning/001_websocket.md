# User Story: Implement Websocket API for ComfyUI Communication

**Goal:** Replace the current HTTP polling mechanism in `handler.py` with ComfyUI's websocket API to monitor prompt execution status and retrieve generated images more efficiently and reliably.

**Current State:**

- `handler.py` queues a prompt via HTTP POST to `/prompt`.
- It then repeatedly polls the `/history/{prompt_id}` endpoint with a delay (`COMFY_POLLING_INTERVAL_MS`) until the job outputs appear in the history.
- Once outputs are detected, `process_output_images` retrieves image filenames from the history, constructs local file paths (assuming images are saved to `/comfyui/output`), checks for file existence, and then either uploads the file from disk to S3 or reads the file from disk to encode it as base64. This reliance on filesystem access is fragile.

**Desired State:**

- Use the ComfyUI websocket API (`ws://<host>/ws?clientId=<clientId>`) for real-time status updates.
- Eliminate the HTTP polling loop and associated constants.
- Retrieve final image data directly using the `/view` API endpoint instead of relying on filesystem access within the container.
- Maintain existing functionality for uploading images to S3 or returning base64 encoded images.

**Tasks:**

1.  **Add Dependency:** Add `websocket-client` to the `requirements.txt` file.
2.  **Modify `handler.py`:**
    - Import `websocket` and `uuid`.
    - Generate a unique `client_id` (using `uuid.uuid4()`) for each job request within the `handler` function.
    - Modify `queue_workflow`: Update the function signature and implementation to accept the `client_id` and include it in the `/prompt` request payload (`{"prompt": workflow, "client_id": client_id}`).
    - **Websocket Connection & Monitoring:**
      - Establish a websocket connection before queuing the prompt: `ws = websocket.WebSocket()` followed by `ws.connect(f"ws://{COMFY_HOST}/ws?clientId={client_id}")`.
      - After queuing the prompt and getting the `prompt_id`, implement the websocket message receiving loop (`while True: out = ws.recv()...`). Listen for the specific `executing` message indicating the prompt is finished (where `message['data']['node'] is None` and `message['data']['prompt_id'] == prompt_id`).
      - Ensure the websocket connection is closed (`ws.close()`) after monitoring is complete or in case of errors (using a `try...finally` block).
    - **Image Retrieval & Handling:**
      - After the websocket indicates completion, call `get_history(prompt_id)` to get the final output structure (as done in the example).
      - Create a new function `get_image_data(filename, subfolder, image_type)` that uses `urllib.request` (or `requests`) to fetch image _bytes_ from the `http://{COMFY_HOST}/view` endpoint.
      - Replace the logic previously in `process_output_images` (or integrate into the main `handler` flow after getting history):
        - Iterate through the `outputs` in the fetched history.
        - For each image identified in the `outputs` dictionary:
          - Call `get_image_data` to retrieve the raw image bytes.
          - If S3 is configured (`BUCKET_ENDPOINT_URL` env var is set):
            - Save the image bytes to a temporary file (using Python's `tempfile` module).
            - Use `rp_upload.upload_image(job_id, temp_file_path)` to upload the temporary file to S3. Determine the correct file extension if possible, default to '.png'.
            - Ensure the temporary file is deleted after upload.
            - Store the returned S3 URL.
          - If S3 is not configured:
            - Base64 encode the image bytes directly.
            - Store the resulting base64 string.
        - Aggregate all resulting image URLs and/or base64 strings into a suitable format (e.g., a list or dictionary).
    - **Cleanup:**
      - Remove the old `process_output_images` function.
      - Remove the polling-related constants (`COMFY_POLLING_INTERVAL_MS`, `COMFY_POLLING_MAX_RETRIES`) and the polling `while` loop.
    - **Error Handling:** Add robust error handling for websocket connection establishment, message receiving/parsing, image data fetching (`/view`), temporary file operations, and S3 uploads.
3.  **Testing:**
    - Update unit tests in `tests/` to mock the websocket interactions and verify the new logic.
    - Perform local end-to-end testing using `docker-compose up` to ensure the integration with a live ComfyUI instance works as expected for both S3 and base64 output modes.

**Considerations:**

- **Websocket Reliability:** Implement try/except blocks around websocket operations. Consider if simple retries are needed for connection failures.
- **Temporary Files for S3:** Using temporary files adds minor overhead but fits the current `runpod` SDK (`rp_upload.upload_image`). Ensure proper cleanup using `try...finally` or context managers.
- **Runpod Lifecycle:** Creating a new websocket connection per `handler` invocation is standard for serverless function executions and ensures isolation.
