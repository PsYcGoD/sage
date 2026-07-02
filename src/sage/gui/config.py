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
        "system_prompts": {
            "claude": ["~/.claude/SAGE-INTEGRATION.md"],
            "codex": ["~/.claude/SAGE-INTEGRATION.md"],
            "gpt4": [],
            "gemini": [],
            "custom": []
        },
        "ai_commands": {
            "claude": "claude",
            "codex": "codex",
            "gpt4": "aichat -m gpt-4",
            "gemini": "aichat -m gemini",
            "custom": ""
        },
        "theme": "dark",
        "auto_compress": True,
        "default_ai": "claude"
    }

    PERSONAL_CONFIG = {
        "personal_mode": True,
        "system_prompts": {
            "claude": [
                "<USER_HOME>\\.claude\\CLAUDE-FABLE-5.md",
                "<USER_HOME>\\.claude\\SAGE-INTEGRATION.md"
            ],
            "codex": ["<USER_HOME>\\.claude\\SAGE-INTEGRATION.md"],
            "gpt4": [],
            "gemini": [],
            "custom": []
        },
        "ai_commands": {
            "claude": "claude --dangerously-skip-permissions",
            "codex": "codex",
            "gpt4": "aichat -m gpt-4",
            "gemini": "aichat -m gemini",
            "custom": ""
        },
        "theme": "dark",
        "auto_compress": True,
        "default_ai": "claude"
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
                    return self._merge_configs(self.DEFAULT_CONFIG.copy(), config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                return self._detect_and_save_config()
        else:
            return self._detect_and_save_config()

    def _detect_and_save_config(self) -> Dict[str, Any]:
        """Detect personal vs public mode and save initial config."""
        # Check if personal mode files exist
        personal_prompt = Path("<USER_HOME>\\.claude\\CLAUDE-FABLE-5.md")
        is_personal = personal_prompt.exists()

        config = self.PERSONAL_CONFIG.copy() if is_personal else self.DEFAULT_CONFIG.copy()

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


# Global config instance
_config_instance: Optional[GUIConfig] = None


def get_config() -> GUIConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = GUIConfig()
    return _config_instance
