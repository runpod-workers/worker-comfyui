---
"worker-comfyui": minor
---

feat: forward ComfyUI per-step progress to RunPod via progress_update

The handler now listens for ComfyUI's `progress` (legacy) and
`progress_state` (current) websocket messages and forwards them through
`runpod.serverless.progress_update` so `/status` polls observe real
intermediate progress instead of only the final `IN_PROGRESS` to
`COMPLETED` jump.

The forwarded payload has a uniform shape regardless of which ComfyUI
event fired it:

```json
{
  "type": "progress",
  "value": 12,
  "max": 25,
  "percent": 48.0,
  "node": "3"
}
```

For `progress_state` messages (which report a snapshot of every node)
`value` and `max` are summed across all nodes belonging to the current
prompt so multi-sampler graphs still produce a single monotonic
percentage. `progress_update` failures are caught and logged so progress
reporting never aborts the job itself.
