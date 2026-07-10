"""SAGE WebSocket server for Electron GUI communication."""

import asyncio
import json
import argparse
import signal
import sys
import uuid
from pathlib import Path

try:
    import websockets
    from websockets.server import serve
except ImportError:
    websockets = None

from sage.store import connect


class SAGEWebSocketServer:
    """WebSocket server bridging Electron GUI to SAGE backend."""

    def __init__(self, port: int = 19480):
        self.port = port
        self.clients: set = set()
        self.running = False
        self._active_processes: dict = {}

    async def handler(self, websocket):
        self.clients.add(websocket)
        try:
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                    response = await self.handle_message(msg)
                    if response:
                        await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "payload": {"message": "Invalid JSON"}
                    }))
        finally:
            self.clients.discard(websocket)

    async def handle_message(self, msg: dict) -> dict | None:
        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})
        msg_id = msg.get("id")

        handlers = {
            "ping": self._handle_ping,
            "session.list": self._handle_session_list,
            "session.create": self._handle_session_create,
            "session.delete": self._handle_session_delete,
            "session.messages": self._handle_session_messages,
            "chat.send": self._handle_chat_send,
            "chat.cancel": self._handle_chat_cancel,
            "provider.list": self._handle_provider_list,
            "provider.status": self._handle_provider_status,
            "settings.get": self._handle_settings_get,
            "settings.set": self._handle_settings_set,
            "metrics.get": self._handle_metrics_get,
            "ml.status": self._handle_ml_status,
        }

        handler = handlers.get(msg_type)
        if handler:
            result = await handler(payload)
            return {"type": f"{msg_type}.response", "payload": result, "id": msg_id}

        return {"type": "error", "payload": {"message": f"Unknown type: {msg_type}"}, "id": msg_id}

    async def _handle_ping(self, payload: dict) -> dict:
        return {"pong": True, "version": "2.0"}

    async def _handle_session_list(self, payload: dict) -> dict:
        try:
            db = connect()
            cursor = db.execute(
                "SELECT id, title, model, agent, created_at, updated_at "
                "FROM chat_sessions ORDER BY updated_at DESC"
            )
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "id": row[0],
                    "title": row[1] or "New Chat",
                    "project": row[3] or "",
                    "created_at": row[4],
                    "updated_at": row[5],
                    "preview": "",
                    "pinned": False,
                    "unread": False,
                })
            return {"sessions": sessions}
        except Exception as e:
            return {"sessions": [], "error": str(e)}

    async def _handle_session_create(self, payload: dict) -> dict:
        project = payload.get("project", "")
        try:
            db = connect()
            session_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO chat_sessions (id, title, model, agent, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                (session_id, "New Chat", "claude-opus-4-6", project)
            )
            db.commit()
            return {"id": session_id, "success": True, "project": project}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_session_delete(self, payload: dict) -> dict:
        session_id = payload.get("id", "")
        try:
            db = connect()
            db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            db.commit()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_session_messages(self, payload: dict) -> dict:
        session_id = payload.get("id", "")
        try:
            db = connect()
            cursor = db.execute(
                "SELECT id, role, content, created_at FROM chat_messages "
                "WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            )
            messages = [
                {"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]}
                for r in cursor.fetchall()
            ]
            return {"messages": messages}
        except Exception:
            return {"messages": []}

    async def _handle_chat_send(self, payload: dict) -> dict:
        session_id = payload.get("session_id", "")
        content = payload.get("content", "")
        if not content:
            return {"status": "error", "message": "Empty message"}

        # Save user message to DB
        try:
            db = connect()
            msg_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO chat_messages (id, session_id, role, content, created_at) "
                "VALUES (?, ?, 'user', ?, datetime('now'))",
                (msg_id, session_id, content)
            )
            db.commit()
        except Exception:
            pass

        asyncio.create_task(self._stream_llm_response(session_id, content))
        return {"status": "streaming"}

    async def _stream_llm_response(self, session_id: str, prompt: str):
        """Stream LLM response via Claude CLI with full thinking/tool events."""
        import shutil

        claude_bin = shutil.which("claude")
        if not claude_bin:
            await self.broadcast({
                "type": "chat.stream.error",
                "payload": {"session_id": session_id, "message": "claude CLI not found in PATH"}
            })
            return

        cmd = [claude_bin, "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", "1"]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            self._active_processes[session_id] = process

            full_text = ""
            full_thinking = ""

            async for chunk in process.stdout:
                line = chunk.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                # Skip non-JSON lines (warnings etc)
                if not line.startswith("{"):
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                evt_type = event.get("type", "")

                if evt_type == "assistant":
                    msg = event.get("message", {})
                    content_blocks = msg.get("content", [])
                    for block in content_blocks:
                        block_type = block.get("type", "")
                        if block_type == "thinking":
                            thinking_text = block.get("thinking", "")
                            if thinking_text:
                                full_thinking += thinking_text
                                await self.broadcast({
                                    "type": "chat.stream.thinking",
                                    "payload": {"session_id": session_id, "text": thinking_text}
                                })
                        elif block_type == "text":
                            text = block.get("text", "")
                            if text:
                                full_text += text
                                await self.broadcast({
                                    "type": "chat.stream.token",
                                    "payload": {"session_id": session_id, "token": text}
                                })
                        elif block_type == "tool_use":
                            tool_name = block.get("name", "")
                            await self.broadcast({
                                "type": "chat.stream.tool",
                                "payload": {
                                    "session_id": session_id,
                                    "name": tool_name,
                                    "id": block.get("id", ""),
                                    "status": "running",
                                }
                            })

                elif evt_type == "result":
                    # Final result — extract text if we missed it
                    result_text = event.get("result", "")
                    if result_text and not full_text:
                        full_text = result_text
                        await self.broadcast({
                            "type": "chat.stream.token",
                            "payload": {"session_id": session_id, "token": result_text}
                        })

            await process.wait()
            self._active_processes.pop(session_id, None)

            # Save assistant message to DB
            save_content = full_text.strip()
            if full_thinking:
                save_content = f"<thinking>{full_thinking}</thinking>\n\n{save_content}"
            if save_content:
                try:
                    db = connect()
                    msg_id = str(uuid.uuid4())
                    db.execute(
                        "INSERT INTO chat_messages (id, session_id, role, content, created_at) "
                        "VALUES (?, ?, 'assistant', ?, datetime('now'))",
                        (msg_id, session_id, save_content)
                    )
                    db.execute(
                        "UPDATE chat_sessions SET updated_at = datetime('now') WHERE id = ?",
                        (session_id,)
                    )
                    db.commit()
                except Exception:
                    pass

            await self.broadcast({
                "type": "chat.stream.done",
                "payload": {"session_id": session_id, "id": str(uuid.uuid4())}
            })

        except Exception as e:
            self._active_processes.pop(session_id, None)
            await self.broadcast({
                "type": "chat.stream.error",
                "payload": {"session_id": session_id, "message": str(e)}
            })

    async def _handle_chat_cancel(self, payload: dict) -> dict:
        session_id = payload.get("session_id", "")
        process = self._active_processes.pop(session_id, None)
        if process:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        return {"status": "cancelled"}

    async def _handle_provider_list(self, payload: dict) -> dict:
        import shutil
        import subprocess

        def check_ollama():
            try:
                r = subprocess.run(["ollama", "list"], capture_output=True, timeout=3)
                return r.returncode == 0
            except Exception:
                return False

        agents = [
            ("claude", "Claude Code", "opus-4.6"),
            ("codex", "Codex CLI", "codex-1"),
            ("opencode", "OpenCode", "auto"),
            ("aider", "Aider", "auto"),
            ("ollama", "Ollama", "local models"),
            ("windsurf", "Windsurf", "auto"),
            ("cursor", "Cursor", "auto"),
            ("cline", "Cline", "auto"),
            ("continue", "Continue", "auto"),
        ]

        providers = []
        for bin_name, display_name, model in agents:
            found = shutil.which(bin_name) is not None
            if bin_name == "ollama":
                found = check_ollama()
            providers.append({
                "id": bin_name,
                "name": display_name,
                "model": model,
                "status": "connected" if found else "not found",
            })
        return {"providers": providers}

    async def _handle_provider_status(self, payload: dict) -> dict:
        return {"provider": payload.get("id", ""), "status": "connected"}

    async def _handle_settings_get(self, payload: dict) -> dict:
        return {"settings": {"permission_mode": "ask", "ml_enabled": True, "compression_enabled": True}}

    async def _handle_settings_set(self, payload: dict) -> dict:
        return {"success": True}

    async def _handle_metrics_get(self, payload: dict) -> dict:
        try:
            db = connect()
            row = db.execute("SELECT COUNT(*), SUM(original_tokens), SUM(compressed_tokens) FROM runs").fetchone()
            total_runs = row[0] or 0
            total_tokens = row[1] or 0
            compressed_tokens = row[2] or 0
            saved = total_tokens - compressed_tokens if total_tokens else 0
            pct = (saved / total_tokens * 100) if total_tokens > 0 else 0
            return {
                "total_runs": total_runs,
                "tokens_processed": total_tokens,
                "tokens_saved": saved,
                "compression_pct": round(pct, 1),
            }
        except Exception:
            return {"total_runs": 0, "tokens_processed": 0, "tokens_saved": 0, "compression_pct": 0}

    async def _handle_ml_status(self, payload: dict) -> dict:
        return {"daemon_running": False, "model_loaded": False}

    async def broadcast(self, msg: dict):
        if self.clients:
            data = json.dumps(msg)
            await asyncio.gather(*[c.send(data) for c in self.clients], return_exceptions=True)

    async def start(self):
        if not websockets:
            print("[SAGE WS] websockets package not installed. Run: pip install websockets")
            sys.exit(1)

        self.running = True
        print(f"[SAGE WS] Starting on ws://localhost:{self.port}")

        async with serve(self.handler, "localhost", self.port):
            stop = asyncio.Future()

            def on_signal():
                stop.set_result(None)

            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, on_signal)
                except NotImplementedError:
                    pass

            print(f"[SAGE WS] Ready on ws://localhost:{self.port}")
            await stop

        print("[SAGE WS] Shutting down")


def main():
    parser = argparse.ArgumentParser(description="SAGE WebSocket server for Electron GUI")
    parser.add_argument("--port", type=int, default=19480, help="WebSocket port (default: 19480)")
    args = parser.parse_args()

    server = SAGEWebSocketServer(port=args.port)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
