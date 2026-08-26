---
"worker-comfyui": minor
---

feat: add `BUCKET_PREFIX` env var to organize S3 uploaded files under a custom prefix path. When set, uses `rp_upload.upload_file_to_bucket` and the path becomes `{prefix}/{job_id}/{original_filename}`. When unset, behavior is unchanged.