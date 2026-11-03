---
"worker-comfyui": minor
---

feat: embed the workflow in generated PNG metadata so output images can be loaded back into ComfyUI

Before this change, ComfyUI was launched with `--disable-metadata` and the handler did not forward `extra_pnginfo` to the `/prompt` endpoint. As a result, generated PNGs did not contain the workflow JSON, and users couldn't drag a result back into the editor to recover the workflow that produced it (#139).

Two changes are required for round-tripping to work:

1. `src/start.sh`: drop `--disable-metadata` from the two `python /comfyui/main.py` invocations.
2. `handler.py`: pass `extra_data: {"extra_pnginfo": {"workflow": workflow}}` in the `/prompt` payload alongside the existing API-format `prompt`. The `extra_pnginfo.workflow` is what the `Save Image` node embeds as the `workflow` key in the PNG.

Side effect: each generated PNG is now ~10-50 KB larger than before (depends on workflow complexity). For users who prefer minimal images, this can be reversed per-job by submitting a payload that uses a workflow without `Save Image` (e.g. only `PreviewImage`), or by post-processing strip on the client.
