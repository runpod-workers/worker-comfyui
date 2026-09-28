import os
from pathlib import Path
import subprocess
import tempfile
import unittest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_INSTALL_SCRIPT = _REPO_ROOT / "scripts" / "comfy-node-install.sh"


class TestComfyNodeInstall(unittest.TestCase):
    def test_installs_node_in_workspace_and_mirrors_requirements_to_runtime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bin_dir = temp_path / "bin"
            bin_dir.mkdir()
            nodes_dir = temp_path / "custom_nodes"
            node_dir = nodes_dir / "test-node"
            node_dir.mkdir(parents=True)
            requirements_file = node_dir / "requirements.txt"
            requirements_file.write_text("test-dependency\n")

            captured_venv = temp_path / "virtual-env"
            captured_uv_args = temp_path / "uv-args"
            comfy = bin_dir / "comfy"
            comfy.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s" "${VIRTUAL_ENV-}" > "$CAPTURED_VENV"\n'
                'echo "Installed test-node"\n'
            )
            comfy.chmod(0o755)
            uv = bin_dir / "uv"
            uv.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s\\n" "$*" >> "$CAPTURED_UV_ARGS"\n'
            )
            uv.chmod(0o755)

            env = os.environ.copy()
            env.pop("VIRTUAL_ENV", None)
            env.update(
                {
                    "CAPTURED_VENV": str(captured_venv),
                    "CAPTURED_UV_ARGS": str(captured_uv_args),
                    "COMFYUI_CUSTOM_NODES_DIR": str(nodes_dir),
                    "COMFYUI_RUNTIME_PYTHON": str(temp_path / "runtime" / "bin" / "python"),
                    "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                }
            )

            result = subprocess.run(
                ["bash", str(_INSTALL_SCRIPT), "test-node"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(captured_venv.read_text(), "")
            self.assertEqual(
                captured_uv_args.read_text().splitlines(),
                [
                    "pip install --python "
                    f"{temp_path / 'runtime' / 'bin' / 'python'} "
                    f"-r {requirements_file}"
                ],
            )


if __name__ == "__main__":
    unittest.main()
