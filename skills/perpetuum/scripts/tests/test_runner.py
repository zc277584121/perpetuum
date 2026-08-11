from pathlib import Path
import tempfile
import unittest
from unittest import mock

from perpetuum_app import storage
from perpetuum_app.runner import Runner


class RunnerTests(unittest.TestCase):
    def make_project(self, root):
        home = root / "home"
        project = root / "project"
        project.mkdir()
        project_id = storage.register_project(
            home,
            project,
            name="测试项目",
            agent="codex",
        )
        return home, project_id

    def test_receipt_completes_top_session_without_screen_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project_id = self.make_project(root)
            runner = Runner(home)
            payloads = runner.project_payloads([project_id])
            run_dir, dispatch, receipt, run_id = runner.create_dispatch(
                "root",
                payloads,
            )
            storage.write_json(
                receipt,
                {
                    "status": "completed",
                    "summary": "完成",
                    "projects": [project_id],
                    "finished_at": storage.utc_now(),
                },
            )
            runner.state["active_root"] = {
                "role": "root",
                "run_id": run_id,
                "session": "perpetuum-root-20260805-120000-a1b2c3",
                "project_ids": [project_id],
                "dispatch_path": str(dispatch),
                "receipt_path": str(receipt),
                "run_dir": str(run_dir),
            }

            with mock.patch(
                "perpetuum_app.runner.sessions.session_exists",
                return_value=True,
            ), mock.patch("perpetuum_app.runner.sessions.kill_session") as kill:
                runner.reconcile_active(
                    "active_root",
                    storage.ensure_home(home),
                )

            self.assertIsNone(runner.state["active_root"])
            self.assertFalse(run_dir.exists())
            kill.assert_called_once_with("perpetuum-root-20260805-120000-a1b2c3")

    def test_dispatch_uses_role_templates_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project_id = self.make_project(root)
            runner = Runner(home)
            payloads = runner.project_payloads([project_id])
            _run_dir, dispatch_path, _receipt, _run_id = runner.create_dispatch(
                "root",
                payloads,
            )

            dispatch = storage.read_json(dispatch_path)
            for key in (
                "root_supervisor",
                "project_supervisor",
                "task_supervisor",
                "explorer",
                "executor",
                "validator",
                "reporter",
            ):
                template = Path(dispatch["references"][key])
                self.assertEqual(template.parent.name, "templates")
                self.assertTrue(template.is_file())

    def test_missing_receipt_creates_control_escalation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project_id = self.make_project(root)
            runner = Runner(home)
            payloads = runner.project_payloads([project_id])
            run_dir, dispatch, receipt, run_id = runner.create_dispatch(
                "root",
                payloads,
            )
            runner.state["active_root"] = {
                "role": "root",
                "run_id": run_id,
                "session": "lost-session",
                "project_ids": [project_id],
                "dispatch_path": str(dispatch),
                "receipt_path": str(receipt),
                "run_dir": str(run_dir),
            }

            with mock.patch(
                "perpetuum_app.runner.sessions.session_exists",
                return_value=False,
            ):
                runner.reconcile_active(
                    "active_root",
                    storage.ensure_home(home),
                )

            escalation = (
                storage.project_dir(home, project_id) / "escalations.md"
            ).read_text()
            self.assertIn("写入完成回执前消失", escalation)
            state = storage.load_project_state(home, project_id)
            self.assertEqual(state["status"], "control_blocked")

    def test_corrupt_run_directory_is_not_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, project_id = self.make_project(root)
            protected = root / "protected"
            protected.mkdir()
            marker = protected / "keep.txt"
            marker.write_text("keep")
            runner = Runner(home)
            runner.state["active_root"] = {
                "role": "root",
                "run_id": "corrupt",
                "session": "unrelated-session",
                "project_ids": [project_id],
                "dispatch_path": str(protected / "dispatch.json"),
                "receipt_path": str(protected / "receipt.json"),
                "run_dir": str(protected),
            }

            runner.reconcile_active(
                "active_root",
                storage.ensure_home(home),
            )

            self.assertEqual(marker.read_text(), "keep")
            self.assertIsNone(runner.state["active_root"])


if __name__ == "__main__":
    unittest.main()
