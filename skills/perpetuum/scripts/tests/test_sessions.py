from pathlib import Path
import shutil
import tempfile
import time
import unittest

from perpetuum_app import sessions


@unittest.skipUnless(shutil.which("tmux"), "tmux is required")
class SessionTests(unittest.TestCase):
    def test_prompt_delivery_uses_unique_tmux_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "received.txt"
            session = sessions.launch_session(
                role="smoke",
                command="bash",
                cwd=root,
                prompt=f'printf "%s" "$TMUX_TMPDIR" > {marker}',
                startup_seconds=1,
                kind="claude",
                tmux_tmpdir=root / "cc-use-tmux",
            )
            try:
                deadline = time.time() + 5
                while time.time() < deadline and not marker.exists():
                    time.sleep(0.1)
                self.assertEqual(marker.read_text(), str(root / "cc-use-tmux"))
                self.assertEqual(
                    (root / "cc-use-tmux").stat().st_mode & 0o777,
                    0o700,
                )
                self.assertTrue(session.startswith("perpetuum-smoke-"))
            finally:
                sessions.kill_session(session)


if __name__ == "__main__":
    unittest.main()
