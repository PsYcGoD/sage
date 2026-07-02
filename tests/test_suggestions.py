import unittest

from sage.store import RunRecord
from sage.suggestions import suggest_next_steps


class SuggestionTests(unittest.TestCase):
    def test_suggests_python_package_install(self):
        record = RunRecord(
            id=1,
            created_at="now",
            project=".",
            command="python app.py",
            exit_code=1,
            duration_ms=10,
            summary="ModuleNotFoundError: No module named 'requests'",
        )
        suggestion = suggest_next_steps(record)
        self.assertIn("python -m pip install requests", suggestion)

    def test_handles_no_history(self):
        suggestion = suggest_next_steps(None)
        self.assertIn("No command history", suggestion)


if __name__ == "__main__":
    unittest.main()
