---
"worker-comfyui": patch
---

fix: pass RELEASE_VERSION as environment variable so docker-bake.hcl resolves versioned tags instead of defaulting to "latest"
