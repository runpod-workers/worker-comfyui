---
"worker-comfyui": patch
---

fix: broaden `allowedCudaVersions` in hub config and lower default log level

- Expand `allowedCudaVersions` in `.runpod/hub.json` and `.runpod/tests_.json` to include `12.8`, `12.9`, and `13.0`. The previous `["12.7", "12.6"]` allow-list excluded the majority of modern Runpod hosts (which run CUDA 12.8+), causing hub deployments to land on incompatible hosts and crash-loop with `nvidia-container-cli: requirement error: unsatisfied condition: cuda>=12.6`.
- Change default `COMFY_LOG_LEVEL` from `DEBUG` to `INFO`. With `DEBUG`, more than 75% of worker log lines were low-level comfy internals (`apply_rope1`, `Backend eager selected`, `aimdo: src/...:DEBUG:`, `Popen([...])`), drowning out the actual handler output. Users who want verbose logs can still set `COMFY_LOG_LEVEL=DEBUG` explicitly.
