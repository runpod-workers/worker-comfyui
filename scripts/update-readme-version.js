/**
 * Updates all `runpod/worker-comfyui:X.Y.Z` version references in README.md
 * to match the current version in package.json.
 *
 * This script is called automatically by `changeset version` via the
 * `changeset:version` npm script.
 */

const fs = require("fs");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
const packageJsonPath = path.join(rootDir, "package.json");
const readmePath = path.join(rootDir, "README.md");

const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf8"));
const version = packageJson.version;

const readme = fs.readFileSync(readmePath, "utf8");
const updated = readme.replace(
  /runpod\/worker-comfyui:\d+\.\d+\.\d+/g,
  `runpod/worker-comfyui:${version}`
);

fs.writeFileSync(readmePath, updated, "utf8");

console.log(`Updated README.md version references to ${version}`);
