import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import Request
from urllib.request import urlopen

from perpetuum_app import storage
from perpetuum_app.server import RuntimeServer


class ServerTests(unittest.TestCase):
    def test_status_and_project_detail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            project_id = storage.register_project(home, project, name="测试项目")
            story = storage.create_story(
                home,
                project_id,
                "完成首个结果",
                "交付可以独立验证的成果",
                priority="P0",
                labels=["research"],
            )
            story_id = story["metadata"]["id"]

            server = RuntimeServer(home, "127.0.0.1", 0)
            port = server.server.server_address[1]
            server.start()
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/status") as response:
                    status = json.loads(response.read())
                self.assertEqual(status["projects"][0]["id"], project_id)

                with urlopen(
                    f"http://127.0.0.1:{port}/api/projects/{project_id}"
                ) as response:
                    detail = json.loads(response.read())
                self.assertIn("goal.md", detail["files"])
                self.assertNotIn("plan.md", detail["files"])
                self.assertEqual(detail["stories"][0]["id"], story_id)

                with urlopen(
                    f"http://127.0.0.1:{port}/api/projects/{project_id}/stories/{story_id}"
                ) as response:
                    story_detail = json.loads(response.read())
                self.assertEqual(story_detail["metadata"]["priority"], "P0")
                self.assertIn("验收标准", story_detail["body"])

                request = Request(
                    f"http://127.0.0.1:{port}/api/projects/{project_id}/stories/{story_id}",
                    data=json.dumps(
                        {"status": "waiting", "priority": "P1", "labels": ["human"]}
                    ).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    result = json.loads(response.read())
                self.assertTrue(result["ok"])
                updated = storage.load_story(home, project_id, story_id)
                self.assertEqual(updated["metadata"]["status"], "waiting")

                request = Request(
                    f"http://127.0.0.1:{port}/api/projects/{project_id}/inbox",
                    data=json.dumps({"text": "优先检查网络"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    result = json.loads(response.read())
                self.assertTrue(result["ok"])
                self.assertIn(
                    "优先检查网络",
                    (storage.project_dir(home, project_id) / "inbox.md").read_text(),
                )

                request = Request(
                    f"http://127.0.0.1:{port}/api/projects/{project_id}/control",
                    data=json.dumps({"action": "pause"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:
                    result = json.loads(response.read())
                self.assertTrue(result["ok"])
                activation = storage.read_json(home / "activation.yaml")
                self.assertTrue(activation["projects"][project_id]["paused"])
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
