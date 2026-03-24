---
"worker-comfyui": major
---

feat!: switch default hub model from FLUX.1-dev-fp8 to FLUX.2 klein 9B (Q5_K_M GGUF)

BREAKING CHANGE: The default hub deployment now uses FLUX.2 klein 9B instead of FLUX.1-dev-fp8.
Existing workflows using CheckpointLoaderSimple with flux1-dev-fp8.safetensors will not work
with the new default image. Use the flux1-dev-fp8 image tag for backward compatibility.
