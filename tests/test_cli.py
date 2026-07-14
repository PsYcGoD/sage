import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from sage import cli
from sage.store import RunRecord


class CliTests(unittest.TestCase):
    def test_explain_defaults_to_latest_run(self):
        record = RunRecord(
            id=4,
            created_at="now",
            project=".",
            command="python --version",
            exit_code=0,
            duration_ms=43,
            summary="Python 3.13.6",
        )
        with patch("sage.cli.latest_run", return_value=record) as latest_run:
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.explain()

        self.assertEqual(code, 0)
        latest_run.assert_called_once_with(only_failures=False)
        self.assertIn("Run #4 succeeded", out.getvalue())

    def test_explain_failed_uses_latest_failure(self):
        record = RunRecord(
            id=3,
            created_at="now",
            project=".",
            command="python app.py",
            exit_code=1,
            duration_ms=150,
            summary="ModuleNotFoundError: No module named requests",
        )
        with patch("sage.cli.latest_run", return_value=record) as latest_run:
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.explain(only_failed=True)

        self.assertEqual(code, 0)
        latest_run.assert_called_once_with(only_failures=True)
        self.assertIn("Run #3 failed", out.getvalue())

    def test_demo_command_shows_first_run_value(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.demo_command()

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("SAGE demo", text)
        self.assertIn("Before: 12,000 tokens", text)
        self.assertIn("After:  800 tokens", text)
        self.assertIn("Saved:  93%", text)
        self.assertIn("Claude", text)
        self.assertIn("Codex", text)
        self.assertIn("25+ AI/dev logs", text)

    def test_demo_main_runs_after_setup_and_enforcement(self):
        calls = []

        with (
            patch("sage.cli._ensure_first_run_setup", side_effect=lambda command: calls.append(("setup", command)) or 0),
            patch("sage.cli._ensure_system_enforcement", side_effect=lambda command: calls.append(("enforce", command)) or True),
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["demo"])

        self.assertEqual(code, 0)
        self.assertEqual(calls, [("setup", "demo"), ("enforce", "demo")])
        self.assertIn("SAGE demo", out.getvalue())


if __name__ == "__main__":
    unittest.main()
