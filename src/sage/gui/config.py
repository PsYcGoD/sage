"""
Configuration loader for SAGE Desktop GUI.

Handles loading GUI configuration from ~/.sage/gui-config.json
with automatic detection of personal vs public mode.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class GUIConfig:
    """Configuration manager for SAGE GUI."""

    DEFAULT_CONFIG = {
        "personal_mode": False,
        "permission_mode": "ask",
        "system_prompts": {
            "claude": ["~/.claude/SAGE-INTEGRATION.md"],
            "bedrock": ["~/.claude/SAGE-INTEGRATION.md"],
            "codex": ["~/.claude/SAGE-INTEGRATION.md"],
            "ollama": ["~/.claude/SAGE-INTEGRATION.md"],
            "gemini": ["~/.claude/SAGE-INTEGRATION.md"],
            "llama": ["~/.claude/SAGE-INTEGRATION.md"],
            "mistral": ["~/.claude/SAGE-INTEGRATION.md"]
        },
        "ai_commands": {
            "claude": "sage run -- claude",
            "bedrock": "direct",
            "codex": "sage run -- codex exec",
            "ollama": "direct",
            "gemini": "sage run -- aichat -m gemini",
            "llama": "sage run -- aichat -m llama",
            "mistral": "sage run -- aichat -m mistral"
        },
        "theme": "dark",
        "output_light_mode": False,
        "run_in_external_terminal": False,
        "run_in_embedded_terminal": True,
        "auto_compress": True,
        "default_ai": "claude",
        "current_project": "",
        "recent_projects": []
    }

    PERSONAL_CONFIG = {
        "personal_mode": True,
        "permission_mode": "full",
        "system_prompts": {
            "claude": [
                "~/.claude/CLAUDE-FABLE-5.md",
                "~/.claude/SAGE-INTEGRATION.md"
            ],
            "codex": ["~/.claude/SAGE-INTEGRATION.md"],
            "ollama": [
                "~/.claude/CLAUDE-FABLE-5.md",
                "~/.claude/SAGE-INTEGRATION.md"
            ],
            "gemini": ["~/.claude/SAGE-INTEGRATION.md"],
            "llama": ["~/.claude/SAGE-INTEGRATION.md"],
            "mistral": ["~/.claude/SAGE-INTEGRATION.md"]
        },
        "ai_commands": {
            "claude": "sage run -- claude --dangerously-skip-permissions",
            "codex": "sage run -- codex exec --dangerously-bypass-approvals-and-sandbox",
            "ollama": "sage run -- ollama run qwen2.5-coder:7b",
            "gemini": "sage run -- aichat -m gemini",
            "llama": "sage run -- aichat -m llama",
            "mistral": "sage run -- aichat -m mistral"
        },
        "theme": "dark",
        "output_light_mode": False,
        "run_in_external_terminal": False,
        "run_in_embedded_terminal": True,
        "auto_compress": True,
        "default_ai": "claude",
        "current_project": "",
        "recent_projects": []
    }

    def __init__(self):
        """Initialize configuration loader."""
        self.config_path = self._get_config_path()
        self.config = self._load_config()

    def _get_config_path(self) -> Path:
        """Get the configuration file path."""
        sage_dir = Path.home() / ".sage"
        sage_dir.mkdir(exist_ok=True)
        return sage_dir / "gui-config.json"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return self._normalize_config(self._merge_configs(self.DEFAULT_CONFIG.copy(), config))
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                return self._detect_and_save_config()
        else:
            return self._detect_and_save_config()

    def _detect_and_save_config(self) -> Dict[str, Any]:
        """Detect personal vs public mode and save initial config."""
        # Check if personal mode files exist
        personal_prompt = Path.home() / ".claude" / "CLAUDE-FABLE-5.md"
        is_personal = personal_prompt.exists()

        config = self._normalize_config(self.PERSONAL_CONFIG.copy() if is_personal else self.DEFAULT_CONFIG.copy())

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")

        return config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two config dictionaries, with override taking precedence."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Keep critical GUI runtime settings consistent."""
        personal_fable = Path.home() / ".claude" / "CLAUDE-FABLE-5.md"
        bundled_fable = Path(__file__).resolve().parent / "assets" / "CLAUDE-FABLE-5.md"
        fable = str(personal_fable if personal_fable.exists() else bundled_fable)
        integration = str(Path.home() / ".claude" / "SAGE-INTEGRATION.md")
        old_admin_fable = "<USER_HOME>\\.claude\\CLAUDE-FABLE-5.md"
        old_admin_integration = "<USER_HOME>\\.claude\\SAGE-INTEGRATION.md"

        prompts = config.setdefault("system_prompts", {})
        for ai in ["claude", "ollama"]:
            values = prompts.get(ai, [])
            if not isinstance(values, list):
                values = []
            blocked = {
                fable,
                integration,
                str(personal_fable),
                str(bundled_fable),
                old_admin_fable,
                old_admin_integration,
                "~/.claude/CLAUDE-FABLE-5.md",
                "~/.claude/SAGE-INTEGRATION.md",
            }
            values = [p for p in values if p and p not in blocked]
            # Keep SAGE integration loaded, then append FABLE-5 last so the
            # user's personal operating profile is not diluted by later files.
            values = [integration, *values, fable]
            prompts[ai] = values

        commands = config.setdefault("ai_commands", {})

        # All commands MUST run through sage wrapper for token tracking
        required_commands = {
            "claude": "sage run -- claude --print --output-format stream-json --include-partial-messages",
            "codex": "sage run -- codex exec --json --skip-git-repo-check",
            "ollama": "sage run -- ollama run qwen2.5-coder:7b",
            "gemini": "sage run -- aichat -m gemini",
            "llama": "sage run -- aichat -m llama",
            "mistral": "sage run -- aichat -m mistral",
        }
        commands.update(required_commands)

        config.setdefault("recent_projects", [])
        config.setdefault("current_project", "")
        config.setdefault("run_in_external_terminal", False)
        config.setdefault("run_in_embedded_terminal", True)
        config.setdefault("anthropic_api_key", "")
        config.setdefault("anthropic_base_url", "")
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save to file."""
        self.config[key] = value
        self.save()

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            print(f"Error saving config: {e}")

    def is_personal_mode(self) -> bool:
        """Check if running in personal mode."""
        return self.config.get("personal_mode", False)

    def get_system_prompts(self, ai: str) -> List[str]:
        """Get system prompt file paths for a specific AI."""
        prompts = self.config.get("system_prompts", {}).get(ai, [])
        # Expand ~ to home directory
        return [os.path.expanduser(p) for p in prompts]

    def get_ai_command(self, ai: str) -> str:
        """Get the command to run for a specific AI."""
        return self.config.get("ai_commands", {}).get(ai, "")

    def get_theme(self) -> str:
        """Get the current theme (dark/light)."""
        return self.config.get("theme", "dark")

    def get_default_ai(self) -> str:
        """Get the default AI selection."""
        return self.config.get("default_ai", "claude")

    def is_auto_compress_enabled(self) -> bool:
        """Check if auto-compression is enabled."""
        return self.config.get("auto_compress", True)

    def get_permission_mode(self) -> str:
        """Get the current permission mode (ask/approve/full)."""
        return self.config.get("permission_mode", "ask")

    def set_permission_mode(self, mode: str) -> None:
        """Set the permission mode."""
        if mode in ["ask", "approve", "full"]:
            self.config["permission_mode"] = mode

    def get_anthropic_api_key(self) -> str:
        return self.config.get("anthropic_api_key", "")

    def get_anthropic_base_url(self) -> str:
        return self.config.get("anthropic_base_url", "")

    def set_anthropic_endpoint(self, api_key: str, base_url: str) -> None:
        self.config["anthropic_api_key"] = api_key.strip()
        self.config["anthropic_base_url"] = base_url.strip()
        self.save()

    def inject_env(self) -> None:
        """Push stored credentials into os.environ so all subprocesses inherit them."""
        # Legacy single-endpoint fields (kept for backward compat)
        key = self.get_anthropic_api_key()
        url = self.get_anthropic_base_url()
        if key and "ANTHROPIC_API_KEY" not in os.environ:
            os.environ["ANTHROPIC_API_KEY"] = key
        if url and "ANTHROPIC_BASE_URL" not in os.environ:
            os.environ["ANTHROPIC_BASE_URL"] = url
        # All per-agent credentials from credential store
        try:
            from sage.gui.credential_store import inject_all
            inject_all()
        except Exception:
            pass


# Global config instance
_config_instance: Optional[GUIConfig] = None


def get_config() -> GUIConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = GUIConfig()
    return _config_instance
