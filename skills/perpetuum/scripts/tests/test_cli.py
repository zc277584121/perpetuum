import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout

from perpetuum_app import cli, storage
from perpetuum_app.server import RuntimeServer


class QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, format_string, *args):
        del format_string, args

    def do_GET(self):
        body = b"unrelated service"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class CliTests(unittest.TestCase):
    def test_start_reuses_existing_perpetuum_frontend(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            storage.ensure_home(home)
            server = RuntimeServer(home, "127.0.0.1", 0)
            port = server.server.server_address[1]
            server.start()
            try:
                output = io.StringIO()
                with mock.patch("perpetuum_app.cli.subprocess.Popen") as popen:
                    with redirect_stdout(output):
                        result = cli.start_service(home, "127.0.0.1", port)
                self.assertEqual(result, 0)
                self.assertIn("直接复用", output.getvalue())
                popen.assert_not_called()
            finally:
                server.stop()

    def test_start_does_not_replace_unrelated_service(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                error = io.StringIO()
                with mock.patch("perpetuum_app.cli.subprocess.Popen") as popen:
                    with redirect_stderr(error):
                        result = cli.start_service(home, "127.0.0.1", port)
                self.assertEqual(result, 1)
                self.assertIn("其他服务占用", error.getvalue())
                popen.assert_not_called()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
