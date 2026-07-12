// SAGE AI Agent Targets - 30 tools supported

export const SAGE_INSTRUCTION = `# SAGE Integration - MANDATORY

This system has SAGE installed. Route every shell command through SAGE.

Rules:
- Every shell command MUST use: \`sage run -- <command>\`
- Every Python command: \`sage run -- python script.py\`
- Every package command: \`sage run -- npm install\`
- Every test command: \`sage run -- pytest\`

Why:
- 97% token compression saves context window
- Tracks command history locally
- ML-powered failure prediction
- Works with all AI coding agents

Examples:
- Wrong: \`python test.py\`
- Correct: \`sage run -- python test.py\`
`;

export const SAGE_INSTRUCTION_SHORT = `# SAGE - Route all commands through: sage run -- <command>`;

export interface AgentTarget {
  name: string;
  path: string;
  instruction: string;
  createIfMissing: boolean;
  fileType: 'markdown' | 'json' | 'yaml';
}

export const AGENT_TARGETS: AgentTarget[] = [
  // Current Python SAGE targets
  { name: 'Claude Code', path: '~/.claude/CLAUDE.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Codex CLI', path: '~/.codex/AGENTS.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Cursor', path: '~/.cursorrules', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Windsurf', path: '~/.windsurfrules', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Cline', path: '~/.cline/AGENTS.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Cline Rules', path: '~/.clinerules', instruction: SAGE_INSTRUCTION_SHORT, createIfMissing: true, fileType: 'markdown' },
  { name: 'OpenCode', path: '~/.config/opencode/AGENTS.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'OpenCode Alt', path: '~/.opencode/AGENTS.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Aider', path: '~/.aider.conf.yml', instruction: SAGE_INSTRUCTION_SHORT, createIfMissing: false, fileType: 'yaml' },
  { name: 'JetBrains AI', path: '~/.junie/guidelines.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  
  // NEW targets for JavaScript V1
  { name: 'GitHub Copilot', path: '~/.github/copilot-instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Amazon Q', path: '~/.aws/amazonq/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Sourcegraph Cody', path: '~/.cody/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Zed AI', path: '~/.config/zed/assistant.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Void', path: '~/.void/AGENTS.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Aide', path: '~/.aide/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Roo Code', path: '~/.roo/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Kodu AI', path: '~/.kodu/AGENTS.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Trae', path: '~/.trae/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Melty', path: '~/.melty/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'PearAI', path: '~/.pearai/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Bolt', path: '~/.bolt/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'SWE-agent', path: '~/.swe-agent/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Continue', path: '~/.continue/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Tabnine', path: '~/.tabnine/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Codeium', path: '~/.codeium/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Supermaven', path: '~/.supermaven/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Augment', path: '~/.augment/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Blackbox AI', path: '~/.blackbox/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
  { name: 'Pieces', path: '~/.pieces/instructions.md', instruction: SAGE_INSTRUCTION, createIfMissing: true, fileType: 'markdown' },
];
