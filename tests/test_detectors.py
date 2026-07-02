import unittest

from signaldeck.detectors import detect_findings, summarize_output


class DetectorTests(unittest.TestCase):
    def test_detects_python_traceback(self):
        text = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'x'\n"
        findings = detect_findings(text)
        self.assertEqual(findings[0].kind, "python-traceback")
        self.assertEqual(findings[1].kind, "python-error")

    def test_success_summary_is_short(self):
        text = "\n".join(f"line {i}" for i in range(20))
        summary = summarize_output(text, "", 0)
        self.assertIn("line 0", summary)
        self.assertIn("more line", summary)

    def test_failed_summary_uses_important_output(self):
        summary = summarize_output("", "npm ERR! missing script: test", 1)
        self.assertIn("npm-error", summary)


if __name__ == "__main__":
    unittest.main()
