import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from perpetuum_app import storage


class StorageTests(unittest.TestCase):
    def test_register_project_creates_self_contained_harness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()

            project_id = storage.register_project(
                home,
                project,
                name="测试项目",
                agent="codex",
                window="00:00-06:00",
            )
            harness = storage.project_dir(home, project_id)

            self.assertTrue((home / "activation.yaml").is_file())
            self.assertTrue((harness / "project.yaml").is_file())
            self.assertTrue((harness / "goal.md").is_file())
            self.assertTrue((harness / "plan.md").is_file())
            self.assertTrue((harness / "history.md").is_file())
            self.assertTrue((harness / "inbox.md").is_file())
            self.assertTrue((harness / "questions.md").is_file())
            self.assertTrue((harness / "escalations.md").is_file())
            self.assertTrue((harness / "reports" / "latest.md").is_file())
            self.assertTrue((harness / "runtime" / "state.json").is_file())
            self.assertTrue((harness / "runtime" / "events.log").is_file())

            activation = json.loads((home / "activation.yaml").read_text())
            project_config = json.loads((harness / "project.yaml").read_text())
            self.assertEqual(project_config["agent"], {"kind": "codex"})
            self.assertEqual(
                activation["projects"][project_id]["windows"],
                ["00:00-06:00"],
            )

    def test_human_message_is_appended(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inbox.md"
            storage.append_human_message(path, "前端指令", "优先检查网络")
            content = path.read_text()
            self.assertIn("前端指令", content)
            self.assertIn("优先检查网络", content)

    def test_project_id_distinguishes_same_directory_name(self):
        first = storage.project_id_for_path(Path("/a/project"))
        second = storage.project_id_for_path(Path("/b/project"))
        self.assertNotEqual(first, second)

    def test_project_windows_can_be_updated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            project_id = storage.register_project(home, project)

            storage.set_project_windows(
                home,
                project_id,
                ["00:00-06:00", "18:00-24:00"],
            )

            activation = storage.read_json(home / "activation.yaml")
            self.assertEqual(
                activation["projects"][project_id]["windows"],
                ["00:00-06:00", "18:00-24:00"],
            )

    def test_claude_environment_takes_priority(self):
        with mock.patch.dict(
            os.environ,
            {"CLAUDECODE": "1", "CODEX_HOME": "/tmp/codex"},
            clear=True,
        ):
            self.assertEqual(storage.detect_agent_kind(), "claude")


if __name__ == "__main__":
    unittest.main()
