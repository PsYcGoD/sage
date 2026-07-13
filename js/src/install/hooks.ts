// SAGE Hooks - enforce mandatory npm/npx SAGE wrapper for AI tools.
import { homedir } from 'os';
import { join, dirname } from 'path';
import { existsSync, writeFileSync, mkdirSync, chmodSync, readFileSync } from 'fs';
import { PYPI_RUN_PREFIX, SAGE_RUN_PREFIX } from './targets.js';

const ENFORCE_SAGE_PY = `#!/usr/bin/env python3
"""SAGE npm enforcement hook - blocks commands not routed through npx SAGE."""
import json
import sys

SAGE_PREFIXES = (${JSON.stringify(SAGE_RUN_PREFIX)}, ${JSON.stringify(PYPI_RUN_PREFIX)})

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = str(data.get("tool_name") or "")
    tool_input = data.get("tool_input") or {}

    if tool_name not in ["Bash", "Shell", "PowerShell", "bash_tool"]:
        return 0

    command = str(tool_input.get("command") or "").strip()
    if any(command.startswith(prefix) for prefix in SAGE_PREFIXES):
        return 0

    print("SAGE enforcement: shell commands must start with one of:", ", ".join(SAGE_PREFIXES), file=sys.stderr)
    print("The blocked command is intentionally not printed to avoid leaking secrets.", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
`;

const ENFORCE_SAGE_JS = `#!/usr/bin/env node
const SAGE_PREFIXES = [${JSON.stringify(SAGE_RUN_PREFIX)}, ${JSON.stringify(PYPI_RUN_PREFIX)}];

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input || '{}');
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};
    if (!['Bash', 'Shell', 'PowerShell', 'bash_tool'].includes(toolName)) process.exit(0);
    const command = String(toolInput.command || '').trim();
    if (SAGE_PREFIXES.some(prefix => command.startsWith(prefix))) process.exit(0);
    console.error('SAGE enforcement: shell commands must start with one of: ' + SAGE_PREFIXES.join(', '));
    console.error('The blocked command is intentionally not printed to avoid leaking secrets.');
    process.exit(2);
  } catch {
    process.exit(0);
  }
});
`;

const CLAUDE_HOOKS_SETTINGS = {
  hooks: {
    PreToolUse: [
      {
        matcher: 'Bash|Shell|PowerShell',
        hooks: [
          {
            type: 'command',
            command: 'python ~/.claude/hooks/enforce_sage.py',
          },
        ],
      },
    ],
  },
};

interface HookTarget {
  name: string;
  hookPath: string;
  settingsPath?: string;
  hookContent: string;
  settingsContent?: object;
}

const HOOK_TARGETS: HookTarget[] = [
  { name: 'Claude Code', hookPath: '~/.claude/hooks/enforce_sage.py', settingsPath: '~/.claude/settings.json', hookContent: ENFORCE_SAGE_PY, settingsContent: CLAUDE_HOOKS_SETTINGS },
  { name: 'Codex CLI', hookPath: '~/.codex/hooks/enforce_sage.py', settingsPath: '~/.codex/config.json', hookContent: ENFORCE_SAGE_PY, settingsContent: { hooks: { pre_command: ['python ~/.codex/hooks/enforce_sage.py'] } } },
  { name: 'OpenCode', hookPath: '~/.config/opencode/hooks/enforce_sage.py', settingsPath: '~/.config/opencode/settings.json', hookContent: ENFORCE_SAGE_PY, settingsContent: { hooks: { PreToolUse: [{ matcher: 'Bash|Shell|PowerShell', hooks: [{ type: 'command', command: 'python ~/.config/opencode/hooks/enforce_sage.py' }] }] } } },
  { name: 'Cline', hookPath: '~/.cline/hooks/enforce_sage.py', settingsPath: '~/.cline/settings.json', hookContent: ENFORCE_SAGE_PY, settingsContent: { hooks: { pre_command: ['python ~/.cline/hooks/enforce_sage.py'] } } },
  { name: 'Cursor', hookPath: '~/.cursor/hooks/enforce_sage.py', hookContent: ENFORCE_SAGE_PY },
  { name: 'Windsurf', hookPath: '~/.windsurf/hooks/enforce_sage.py', hookContent: ENFORCE_SAGE_PY },
  { name: 'Aider', hookPath: '~/.aider/hooks/enforce_sage.py', hookContent: ENFORCE_SAGE_PY },
  { name: 'JetBrains AI', hookPath: '~/.junie/hooks/enforce_sage.py', hookContent: ENFORCE_SAGE_PY },
];

export async function installHooks(): Promise<number> {
  let installed = 0;

  for (const target of HOOK_TARGETS) {
    try {
      const success = await installHook(target);
      if (success) installed++;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.warn(`SAGE: could not install ${target.name} hook (${message})`);
    }
  }

  return installed;
}

async function installHook(target: HookTarget): Promise<boolean> {
  const hookPath = expandPath(target.hookPath);
  const hookDir = dirname(hookPath);

  if (!existsSync(hookDir)) {
    mkdirSync(hookDir, { recursive: true });
  }

  writeFileSync(hookPath, target.hookContent, 'utf-8');

  try {
    chmodSync(hookPath, '755');
  } catch {
    // Windows does not need chmod.
  }

  if (target.settingsPath && target.settingsContent) {
    const settingsPath = expandPath(target.settingsPath);
    const settingsDir = dirname(settingsPath);
    if (!existsSync(settingsDir)) {
      mkdirSync(settingsDir, { recursive: true });
    }

    let settings: any = {};
    if (existsSync(settingsPath)) {
      try {
        settings = JSON.parse(readFileSync(settingsPath, 'utf-8'));
      } catch {
        settings = {};
      }
    }

    settings.hooks = mergeHooks(settings.hooks, (target.settingsContent as any).hooks);
    writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
  }

  return true;
}

function mergeHooks(existing: any, incoming: any): any {
  if (!existing || typeof existing !== 'object') {
    return incoming;
  }
  const merged = { ...existing };
  for (const [key, value] of Object.entries(incoming || {})) {
    if (Array.isArray(value) && Array.isArray(merged[key])) {
      for (const item of value) {
        const encoded = JSON.stringify(item);
        if (!merged[key].some((existingItem: any) => JSON.stringify(existingItem) === encoded)) {
          merged[key].push(item);
        }
      }
    } else if (merged[key] === undefined) {
      merged[key] = value;
    } else if (
      merged[key] &&
      typeof merged[key] === 'object' &&
      value &&
      typeof value === 'object' &&
      !Array.isArray(value)
    ) {
      merged[key] = mergeHooks(merged[key], value);
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

function expandPath(path: string): string {
  if (path.startsWith('~/') || path.startsWith('~\\') || path === '~') {
    const rest = path.slice(1).replace(/^[/\\]/, '');
    return rest ? join(homedir(), rest) : homedir();
  }
  return path;
}

export { HOOK_TARGETS, ENFORCE_SAGE_PY, ENFORCE_SAGE_JS };
