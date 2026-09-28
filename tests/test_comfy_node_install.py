import os
from pathlib import Path
import subprocess
import tempfile
import unittest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_INSTALL_SCRIPT = _REPO_ROOT / "scripts" / "comfy-node-install.sh"


class TestComfyNodeInstall(unittest.TestCase):
    def test_installs_custom_node_in_runtime_venv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bin_dir = temp_path / "bin"
            bin_dir.mkdir()
            captured_venv = temp_path / "virtual-env"
            comfy = bin_dir / "comfy"
            comfy.write_text(
                "#!/usr/bin/env bash\n"
                'printf "%s" "$VIRTUAL_ENV" > "$CAPTURED_VENV"\n'
                'echo "Installed test-node"\n'
            )
            comfy.chmod(0o755)

            env = os.environ.copy()
            env.pop("VIRTUAL_ENV", None)
            env["CAPTURED_VENV"] = str(captured_venv)
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

            result = subprocess.run(
                ["bash", str(_INSTALL_SCRIPT), "test-node"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(captured_venv.read_text(), "/opt/venv")


if __name__ == "__main__":
    unittest.main()
