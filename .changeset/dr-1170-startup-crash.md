---
"worker-comfyui": patch
---

Fix ComfyUI startup crash that surfaced as `ComfyUI server (127.0.0.1:8188) not reachable after multiple retries`. ComfyUI's full runtime dependency set is now installed into the same virtualenv that `start.sh` launches ComfyUI with, so the server starts reliably. Also pins `transformers<5` / `huggingface-hub<1`, adds a build-time smoke test that fails the build if ComfyUI can't start, and the GPU pre-flight now launches a real kernel for a clear error on a kernel/arch mismatch.
