"""Native CLI integration - uses actual Claude/Codex CLIs (already logged in!)"""

import subprocess
import threading
import queue
import os
from typing import Generator


class NativeCLIClient:
    """Wrapper for native CLI tools (claude, codex) - uses their existing auth"""

    def __init__(self, ai_name: str, system_prompts: list[str] | None = None):
        self.ai_name = ai_name.lower()
        self.system_prompts = system_prompts or []
        self.process = None

    def _subprocess_env(self) -> dict | None:
        """Force Codex to use its CLI login instead of a possibly stale API key env var."""
        if self.ai_name != "codex":
            return None

        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        return env

    def stream_response(self, prompt: str) -> Generator[tuple[str, str], None, None]:
        """Stream response from native CLI"""

        # Build command based on AI (always through sage run for token tracking).
        # Claude loads CLAUDE-FABLE-5.md + SAGE-INTEGRATION.md globally via
        # ~/.claude/CLAUDE.md, so no --append-system-prompt-file needed here.
        if self.ai_name == "claude":
            cmd = ["sage", "run", "--", "claude", "--print"]

        elif self.ai_name == "codex":
            cmd = ["sage", "run", "--", "codex", "exec", "--skip-git-repo-check"]

        else:
            yield ("error", f"\n[ERROR] Unknown AI: {self.ai_name}\n")
            return

        try:
            yield ("status", f"[Working...] Starting {self.ai_name}...\n")

            # Run CLI with stdin
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=self._subprocess_env()
            )

            # Send prompt
            if self.process.stdin:
                self.process.stdin.write(prompt)
                self.process.stdin.close()

            # Stream output
            output_queue = queue.Queue()

            def read_stream(stream, name):
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            output_queue.put((name, line))
                finally:
                    output_queue.put((name, None))

            # Start threads
            stdout_thread = threading.Thread(
                target=read_stream,
                args=(self.process.stdout, 'stdout'),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream,
                args=(self.process.stderr, 'stderr'),
                daemon=True
            )

            stdout_thread.start()
            stderr_thread.start()

            # Stream output
            streams_done = {"stdout": False, "stderr": False}

            while not all(streams_done.values()):
                try:
                    stream_name, line = output_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if line is None:
                    streams_done[stream_name] = True
                    continue

                # Output the line
                yield ("text", line)

            # Wait for process
            exit_code = self.process.wait()

            if exit_code == 0:
                yield ("complete", "\n")
            else:
                yield ("error", f"\n[ERROR] Process exited with code {exit_code}\n")

        except FileNotFoundError:
            yield ("error", f"\n[ERROR] '{self.ai_name}' CLI not found. Is it installed?\n")
        except Exception as e:
            yield ("error", f"\n[ERROR] {e}\n")

    def stop(self):
        """Stop the running process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()


def check_native_cli_available(ai_name: str) -> bool:
    """Check if native CLI is available and logged in"""
    import shutil

    ai_name = ai_name.lower()

    if ai_name == "claude":
        # Check if claude CLI exists
        if not shutil.which("claude"):
            return False

        # Check auth status
        try:
            result = subprocess.run(
                ["claude", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # If logged in, output will contain "loggedIn": true
            return '"loggedIn": true' in result.stdout or 'loggedIn: true' in result.stdout
        except:
            return False

    elif ai_name == "codex":
        # Check if codex CLI exists
        if not shutil.which("codex"):
            return False

        # Check login status
        try:
            env = os.environ.copy()
            env.pop("OPENAI_API_KEY", None)
            result = subprocess.run(
                ["sage", "run", "--", "codex", "login", "status"],
                capture_output=True,
                text=True,
                timeout=15,
                env=env
            )
            # If logged in, output will say "Logged in"
            return "Logged in" in f"{result.stdout}\n{result.stderr}"
        except:
            return False

    return False
