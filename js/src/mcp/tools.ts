// SAGE MCP Tools - All tool definitions and handlers
import { runCommand, parseCommand } from '../runner/index.js';
import { Database } from '../db/index.js';
import { compress } from '../compression/index.js';
import { FailurePredictor } from '../ml/index.js';
import { selectAgents } from '../agents/index.js';

export const TOOLS = [
  {
    name: 'sage_run',
    description: 'Run a command with SAGE compression and tracking. Returns compressed output.',
    inputSchema: {
      type: 'object',
      properties: {
        command: {
          type: 'string',
          description: 'Command to execute'
        }
      },
      required: ['command']
    }
  },
  {
    name: 'sage_read_file',
    description: 'Read a file with SAGE compression for large files.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File path to read' },
        lines: { type: 'string', description: 'Optional line range START:END' },
        raw: { type: 'boolean', description: 'Return exact content without compression' }
      },
      required: ['path']
    }
  },
  {
    name: 'sage_write_file',
    description: 'Write content to a file.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File path to write' },
        content: { type: 'string', description: 'Content to write' },
        overwrite: { type: 'boolean', description: 'Allow overwriting existing file' }
      },
      required: ['path', 'content']
    }
  },
  {
    name: 'sage_edit_file',
    description: 'Edit a file by replacing exact string matches.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File path to edit' },
        old: { type: 'string', description: 'Exact string to replace' },
        new: { type: 'string', description: 'Replacement string' }
      },
      required: ['path', 'old', 'new']
    }
  },
  {
    name: 'sage_grep',
    description: 'Search files for a pattern.',
    inputSchema: {
      type: 'object',
      properties: {
        pattern: { type: 'string', description: 'Regex pattern to search' },
        paths: { type: 'array', items: { type: 'string' }, description: 'Paths to search' },
        glob: { type: 'string', description: 'Filename filter like *.py' }
      },
      required: ['pattern']
    }
  },
  {
    name: 'sage_glob',
    description: 'Find files matching a pattern.',
    inputSchema: {
      type: 'object',
      properties: {
        pattern: { type: 'string', description: 'Glob pattern like **/*.ts' },
        root: { type: 'string', description: 'Root directory' }
      },
      required: ['pattern']
    }
  },
  {
    name: 'sage_tree',
    description: 'Show directory tree.',
    inputSchema: {
      type: 'object',
      properties: {
        root: { type: 'string', description: 'Root directory' },
        depth: { type: 'number', description: 'Max depth' }
      }
    }
  },
  {
    name: 'sage_get_history',
    description: 'Get recent command history.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Max entries to return' },
        failed_only: { type: 'boolean', description: 'Only show failed commands' }
      }
    }
  },
  {
    name: 'sage_explain_error',
    description: 'Get explanation for a command error.',
    inputSchema: {
      type: 'object',
      properties: {
        command_id: { type: 'number', description: 'Command ID to explain' }
      }
    }
  },
  {
    name: 'sage_suggest_fix',
    description: 'Get suggested fix for a failed command.',
    inputSchema: {
      type: 'object',
      properties: {
        command_id: { type: 'number', description: 'Command ID to suggest fix for' }
      }
    }
  },
  {
    name: 'sage_spawn_agent',
    description: 'Spawn a SAGE agent for a specific task.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_type: {
          type: 'string',
          enum: ['code', 'debug', 'test', 'security'],
          description: 'Agent type to spawn'
        },
        task: { type: 'string', description: 'Task description' }
      },
      required: ['agent_type', 'task']
    }
  }
];

export async function handleToolCall(name: string, args: Record<string, unknown>): Promise<unknown> {
  const db = Database.getInstance();

  switch (name) {
    case 'sage_run': {
      const command = args.command as string;
      const { command: cmd, args: cmdArgs } = parseCommand(command);
      const result = await runCommand(cmd, cmdArgs);
      
      return {
        success: result.exitCode === 0,
        exit_code: result.exitCode,
        run_id: result.runId,
        compression: {
          original_tokens: result.compression.originalTokens,
          compressed_tokens: result.compression.compressedTokens,
          saved_tokens: result.compression.savedTokens,
          compression_ratio: result.compression.compressionRatio
        },
        output: result.compression.compressed,
        duration_ms: result.durationMs
      };
    }

    case 'sage_read_file': {
      const { readFileSync, existsSync } = await import('fs');
      const path = args.path as string;
      
      if (!existsSync(path)) {
        return { success: false, error: `File not found: ${path}` };
      }

      const content = readFileSync(path, 'utf-8');
      const lines = args.lines as string | undefined;
      
      if (lines) {
        const [start, end] = lines.split(':').map(Number);
        const allLines = content.split('\n');
        const selected = allLines.slice(start - 1, end === -1 ? undefined : end);
        return { success: true, content: selected.join('\n'), lines: selected.length };
      }

      if (args.raw) {
        return { success: true, content, lines: content.split('\n').length };
      }

      // Compress large files
      const compression = compress(content, 0);
      return {
        success: true,
        content: compression.compressed,
        original_tokens: compression.originalTokens,
        compressed_tokens: compression.compressedTokens
      };
    }

    case 'sage_write_file': {
      const { writeFileSync, existsSync, mkdirSync } = await import('fs');
      const { dirname } = await import('path');
      const path = args.path as string;
      const content = args.content as string;
      
      if (existsSync(path) && !args.overwrite) {
        return { success: false, error: 'File exists. Set overwrite: true to replace.' };
      }

      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, content, 'utf-8');
      
      return { success: true, bytes: content.length, lines: content.split('\n').length };
    }

    case 'sage_edit_file': {
      const { readFileSync, writeFileSync, existsSync } = await import('fs');
      const path = args.path as string;
      const oldStr = args.old as string;
      const newStr = args.new as string;
      
      if (!existsSync(path)) {
        return { success: false, error: `File not found: ${path}` };
      }

      const content = readFileSync(path, 'utf-8');
      const count = (content.match(new RegExp(oldStr.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
      
      if (count === 0) {
        return { success: false, error: 'String not found in file' };
      }
      if (count > 1) {
        return { success: false, error: `String found ${count} times. Must be unique.` };
      }

      const newContent = content.replace(oldStr, newStr);
      writeFileSync(path, newContent, 'utf-8');
      
      return { success: true, replaced: 1 };
    }

    case 'sage_get_history': {
      const limit = (args.limit as number) || 10;
      const failedOnly = args.failed_only as boolean;
      
      let runs = db.getRecentRuns(limit * 2);
      if (failedOnly) {
        runs = runs.filter(r => r.exitCode !== 0);
      }
      runs = runs.slice(0, limit);

      return {
        success: true,
        runs: runs.map(r => ({
          id: r.id,
          command: r.command,
          exit_code: r.exitCode,
          saved_tokens: r.originalTokens - r.compressedTokens,
          created_at: r.createdAt
        }))
      };
    }

    case 'sage_explain_error': {
      const id = args.command_id as number | undefined;
      const run = id ? db.getRunById(id) : db.getLatestFailedRun();
      
      if (!run) {
        return { success: false, error: 'No command found' };
      }

      return {
        success: true,
        command: run.command,
        exit_code: run.exitCode,
        output: run.compressed,
        explanation: analyzeError(run.compressed || run.stderr)
      };
    }

    case 'sage_suggest_fix': {
      const id = args.command_id as number | undefined;
      const run = id ? db.getRunById(id) : db.getLatestFailedRun();
      
      if (!run) {
        return { success: false, error: 'No command found' };
      }

      return {
        success: true,
        command: run.command,
        suggestions: generateSuggestions(run.command, run.compressed || run.stderr)
      };
    }

    case 'sage_spawn_agent': {
      const agentType = args.agent_type as string;
      const task = args.task as string;
      const agents = selectAgents(task);
      const matched = agents.find(a => a.type === agentType);
      
      if (!matched) {
        return { success: false, error: `Unknown agent type: ${agentType}` };
      }

      return {
        success: true,
        agent: matched,
        task,
        status: 'Agent patterns applied to task analysis'
      };
    }

    default:
      return { success: false, error: `Unknown tool: ${name}` };
  }
}

function analyzeError(output: string): string {
  const lower = output.toLowerCase();
  
  if (lower.includes('modulenotfounderror')) return 'Missing Python module. Install with pip.';
  if (lower.includes('cannot find module')) return 'Missing Node module. Install with npm.';
  if (lower.includes('syntaxerror')) return 'Syntax error in code. Check the file and line.';
  if (lower.includes('permission denied')) return 'Permission issue. Check file permissions or use sudo.';
  if (lower.includes('command not found')) return 'Command not installed or not in PATH.';
  if (lower.includes('connection refused')) return 'Service not running. Start the server first.';
  
  return 'Review the error output for details.';
}

function generateSuggestions(command: string, output: string): string[] {
  const suggestions: string[] = [];
  const lower = output.toLowerCase();
  
  if (lower.includes('modulenotfounderror')) {
    const match = output.match(/No module named '([^']+)'/);
    if (match) suggestions.push(`pip install ${match[1]}`);
  }
  if (lower.includes('cannot find module')) {
    const match = output.match(/Cannot find module '([^']+)'/);
    if (match) suggestions.push(`npm install ${match[1]}`);
  }
  if (lower.includes('permission denied')) {
    suggestions.push('Run with elevated privileges (sudo or administrator)');
  }
  
  return suggestions.length ? suggestions : ['Review the error and fix the underlying issue'];
}
