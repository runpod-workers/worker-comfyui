---
"worker-comfyui": patch
---

ci: build base image on every pull request so PR changes are testable before merge

Previously the `Development` workflow only ran on manual `workflow_dispatch`, and `release.yml` only built images after a `chore: version packages` commit landed on `main`. That meant fixes couldn't be deployed and tested on a real Runpod endpoint until they were already merged. With this change, opening or pushing to a PR builds and pushes a `base` image tagged with the branch slug (e.g. `:fix-pin-boto3`), so reviewers can deploy that exact image to a serverless endpoint and verify behavior before approval.
