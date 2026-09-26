---
"worker-comfyui": patch
---

fix: pin `boto3<1.40` so S3 uploads to non-AWS providers (Cloudflare R2, Google Cloud Storage) keep working

boto3 1.40 ships a botocore release that enforces stricter AWS-only auth flows; uploads to S3-compatible endpoints like GCS and R2 began failing with `SignatureDoesNotMatch`. The fix is a version pin until upstream `runpod` and `aioboto3` stabilize on the new botocore. Reporter on #156 isolated this exactly: `boto3==1.35.40` works, `1.40.1` breaks.
