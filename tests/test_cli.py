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


if __name__ == "__main__":
    unittest.main()
