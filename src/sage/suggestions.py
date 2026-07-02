from __future__ import annotations

import re

from .store import RunRecord


def suggest_next_steps(record: RunRecord | None) -> str:
    if record is None:
        return "\n".join(
            [
                "No command history yet.",
                "Try: sage run -- python --version",
            ]
        )

    text = f"{record.command}\n{record.summary}"
    lower = text.lower()
    steps: list[str] = []

    if "modulenotfounderror" in lower or "no module named" in lower:
        package = _extract_missing_python_package(text)
        if package:
            steps.append(f"Install or add the missing Python package: python -m pip install {package}")
        steps.append("Check whether your virtual environment is active.")
        steps.append("Run: python -m pip list")

    elif "npm err!" in lower and "missing script" in lower:
        steps.append("Open package.json and check the scripts section.")
        steps.append("Run: npm run")
        steps.append("Use one of the listed scripts, for example: sage run -- npm run test")

    elif "ts" in lower and "typescript-error" in lower:
        steps.append("Run the TypeScript compiler with no emit: sage run -- npx tsc --noEmit")
        steps.append("Open the file and line mentioned in the TypeScript error.")

    elif "pytest" in lower or "test-failure" in lower:
        steps.append("Run the failing test with more detail.")
        steps.append("For pytest: sage run -- pytest -x -vv")
        steps.append("For unittest: sage run -- python -m unittest -v")

    elif "git" in lower and "fatal" in lower:
        steps.append("Check the current Git state: sage run -- git status")
        steps.append("Check remotes: sage run -- git remote -v")

    elif record.exit_code == 0:
        steps.append("The latest command succeeded. No fix is needed.")
        steps.append("Next useful check: sage history")

    else:
        steps.append("Read the important output above and identify the first error line.")
        steps.append("Run the command again with a narrower target if possible.")
        steps.append("Ask Claude or Codex to inspect the file mentioned in the first error.")

    return "\n".join(f"- {step}" for step in steps)


def _extract_missing_python_package(text: str) -> str | None:
    match = re.search(r"No module named ['\"]?([A-Za-z0-9_.-]+)['\"]?", text)
    if not match:
        return None
    return match.group(1).split(".")[0].replace("-", "_")
