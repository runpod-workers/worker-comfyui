# User Story: Restructure Documentation for Clarity and Maintainability

**Goal:** Refactor the main `README.md` to focus on essential user information (deployment, configuration basics, API usage) and move detailed sections (customization, local development, CI/CD, etc.) into separate, focused documents within the `docs/` directory. Improve overall documentation structure and ease of navigation.

**Current State:**

- The `README.md` file is very large and covers a wide range of topics, from basic usage to advanced customization and development setup.
- It can be difficult for users to quickly find the specific information they need (e.g., just how to run the API vs. how to build a custom image).
- The release process (`.releaserc`) currently updates version numbers only within `README.md` using a `sed` command.

**Desired State:**

- A concise `README.md` serving as a landing page and quickstart guide, containing:
  - Brief introduction/purpose.
  - Quickstart guide (linking to detailed deployment).
  - List of available pre-built images (with current version tags).
  - Essential configuration (S3 setup, linking to full config).
  - API specification (endpoints, input/output formats).
  - Basic API interaction examples (linking to details if needed).
  - How to get the ComfyUI workflow JSON.
  - Clear links to more detailed documentation in the `docs/` directory.
- New documents created within `docs/` covering specific topics:
  - `docs/deployment.md`: Detailed RunPod template/endpoint creation, GPU recommendations.
  - `docs/configuration.md`: Comprehensive list and explanation of all environment variables.
  - `docs/customization.md`: In-depth guide on using Network Volumes and building custom Docker images (models, nodes, snapshots).
  - `docs/development.md`: Instructions for local setup (Python, WSL), running tests, using `docker-compose`, accessing local API/ComfyUI.
  - `docs/ci-cd.md`: Explanation of the GitHub Actions workflows for Docker Hub deployment (secrets, variables).
  - `docs/acknowledgments.md`: (Optional) Move acknowledgments here.
- Specific version numbers (e.g., `3.6.0` in image tags) should ideally only reside in the main `README.md` to avoid complicating the release script. If version numbers must exist in other files, the `.releaserc` `prepareCmd` will need modification.

**Tasks:**

1.  **Create New Files:** Create the following new markdown files within the `docs/` directory: `deployment.md`, `configuration.md`, `customization.md`, `development.md`, `ci-cd.md`, (optionally `acknowledgments.md`).
2.  **Migrate Content:** Carefully move relevant sections from the current `README.md` into the corresponding new files in `docs/`. Ensure content flows logically within each new document.
3.  **Refactor `README.md`:** Rewrite and condense `README.md` to focus on the core user information identified in the "Desired State". Remove migrated content.
4.  **Add Links:** Insert clear links within the refactored `README.md` pointing to the detailed information in the new `docs/` files (e.g., "For detailed deployment steps, see [Deployment Guide](docs/deployment.md)."). Also, ensure inter-linking between new docs where relevant.
5.  **Review Versioning:** Scrutinize all documentation files (`README.md` and `docs/*`) to ensure specific version numbers (like image tags) are confined to `README.md` where possible.
6.  **Verify Release Script:** Confirm that the existing `prepareCmd` in `.releaserc` is still sufficient (targets the right file and pattern for version replacement). If version numbers were unavoidably moved outside `README.md`, update the `sed` command accordingly to target the additional files.
7.  **Review and Test:** Read through the restructured documentation to ensure clarity, accuracy, and completeness. Verify all internal links work correctly.

**Considerations:**

- **Discoverability:** While splitting improves focus, ensure the main `README.md` provides good entry points/links so users can find detailed information.
- **Consistency:** Maintain consistent formatting and tone across all documentation files.
- **Versioning Maintenance:** Keeping version numbers primarily in `README.md` simplifies the release automation script.
