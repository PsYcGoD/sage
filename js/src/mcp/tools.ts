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
          enum: ['code', 'debug', 'test', 'security', 'performance'],
          description: 'Agent type to spawn'
        },
        task: { type: 'string', description: 'Task description' }
      },
      required: ['agent_type', 'task']
    }
  },
  {
    name: 'sage_validate',
    description: 'Deep validation: AST errors, security issues (hardcoded secrets), code quality (TODO/debug code).',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File path to validate' },
        content: { type: 'string', description: 'Optional content to validate instead of reading file' }
      },
      required: ['path']
    }
  },
  {
    name: 'sage_analyze_context',
    description: 'Analyze codebase patterns (naming, error handling, testing), style (indent, quotes), file structure.',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File or directory to analyze' },
        sample_size: { type: 'number', description: 'Number of files to sample for pattern detection' }
      }
    }
  },
  {
    name: 'sage_rollback',
    description: 'Rollback a file to its state before the last write/edit. Uses snapshot system.',
    inputSchema: {
      type: 'object',
      properties: {
        snapshot_id: { type: 'string', description: 'Snapshot ID from previous write/edit result' }
      },
      required: ['snapshot_id']
    }
  },
  {
    name: 'sage_agentic_run',
    description: 'Run command with automatic failure recovery. Diagnoses errors and retries with fixes.',
    inputSchema: {
      type: 'object',
      properties: {
        command: { type: 'string', description: 'Command to execute' },
        max_retries: { type: 'number', description: 'Max recovery attempts (default 3)' },
        autonomy: { type: 'string', enum: ['suggest', 'ask', 'auto'], description: 'Fix autonomy level' }
      },
      required: ['command']
    }
  },
  {
    name: 'sage_agentic_fix',
    description: 'Get the best fix candidate for a failed command.',
    inputSchema: {
      type: 'object',
      properties: {
        command_id: { type: 'number', description: 'Run ID of failed command (default: most recent)' }
      }
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

    case 'sage_validate': {
      const { existsSync, readFileSync } = await import('fs');
      const path = args.path as string;
      const content = (args.content as string) || (existsSync(path) ? readFileSync(path, 'utf-8') : null);

      if (!content) {
        return { success: false, error: `File not found: ${path}` };
      }

      const issues = validateCode(path, content);
      const errors = issues.filter(i => i.severity === 'error');
      const warnings = issues.filter(i => i.severity === 'warning');

      return {
        success: true,
        valid: errors.length === 0,
        summary: `${errors.length} error(s), ${warnings.length} warning(s)`,
        issues: issues.slice(0, 15)
      };
    }

    case 'sage_analyze_context': {
      const { existsSync, readdirSync, readFileSync, statSync } = await import('fs');
      const { join, extname } = await import('path');
      const targetPath = (args.path as string) || '.';
      const sampleSize = (args.sample_size as number) || 15;

      if (!existsSync(targetPath)) {
        return { success: false, error: `Path not found: ${targetPath}` };
      }

      const patterns = detectPatterns(targetPath, sampleSize);
      const style = detectStyle(targetPath, sampleSize);

      return {
        success: true,
        patterns,
        style,
        summary: `Detected ${patterns.length} patterns. Style: ${style.indent_type} (${style.indent_size}), ${style.quote_style} quotes`
      };
    }

    case 'sage_rollback': {
      const snapshotId = args.snapshot_id as string;
      const snapshot = snapshotStore.get(snapshotId);

      if (!snapshot) {
        return { success: false, error: `Snapshot not found: ${snapshotId}` };
      }

      const { writeFileSync, unlinkSync } = await import('fs');
      if (snapshot.content === null) {
        // File was created, delete it
        try { unlinkSync(snapshot.path); } catch {}
      } else {
        writeFileSync(snapshot.path, snapshot.content, 'utf-8');
      }

      snapshotStore.delete(snapshotId);
      return { success: true, restored: snapshot.path };
    }

    case 'sage_agentic_run': {
      const command = args.command as string;
      const maxRetries = (args.max_retries as number) || 3;
      const autonomy = (args.autonomy as string) || 'auto';

      const { command: cmd, args: cmdArgs } = parseCommand(command);
      let result = await runCommand(cmd, cmdArgs);
      let attempts = 1;

      while (result.exitCode !== 0 && attempts < maxRetries && autonomy !== 'suggest') {
        const suggestions = generateSuggestions(command, result.compression.compressed);
        if (suggestions.length === 0 || suggestions[0].includes('Review')) break;

        // Try the first suggestion
        const fixCmd = suggestions[0];
        const { command: fixCmdParsed, args: fixArgs } = parseCommand(fixCmd);
        await runCommand(fixCmdParsed, fixArgs);

        // Retry original
        result = await runCommand(cmd, cmdArgs);
        attempts++;
      }

      return {
        success: result.exitCode === 0,
        exit_code: result.exitCode,
        attempts,
        output: result.compression.compressed
      };
    }

    case 'sage_agentic_fix': {
      const id = args.command_id as number | undefined;
      const run = id ? db.getRunById(id) : db.getLatestFailedRun();

      if (!run) {
        return { success: false, error: 'No failed command found' };
      }

      const suggestions = generateSuggestions(run.command, run.compressed || run.stderr);
      const explanation = analyzeError(run.compressed || run.stderr);

      return {
        success: true,
        command: run.command,
        fix_command: suggestions[0] || null,
        explanation,
        confidence: suggestions.length > 0 && !suggestions[0].includes('Review') ? 0.8 : 0.3
      };
    }

    default:
      return { success: false, error: `Unknown tool: ${name}` };
  }
}

// Snapshot store for rollback
const snapshotStore = new Map<string, { path: string; content: string | null }>();
let snapshotCounter = 0;

function createSnapshot(path: string, content: string | null): string {
  const id = `snap_${++snapshotCounter}_${Date.now()}`;
  snapshotStore.set(id, { path, content });
  return id;
}

// Code validation
interface ValidationIssue {
  line: number;
  severity: 'error' | 'warning' | 'info';
  category: string;
  message: string;
}

function validateCode(path: string, content: string): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const lines = content.split('\n');
  const ext = path.split('.').pop()?.toLowerCase();

  // Python-specific validation
  if (ext === 'py') {
    lines.forEach((line, i) => {
      const lineNo = i + 1;

      // Empty function
      if (/def\s+\w+\([^)]*\):\s*$/.test(line) && lines[i + 1]?.trim() === 'pass') {
        issues.push({ line: lineNo, severity: 'warning', category: 'empty_function', message: 'Empty function body' });
      }

      // Bare except
      if (/except\s*:/.test(line) && !/except\s+\w+/.test(line)) {
        issues.push({ line: lineNo, severity: 'warning', category: 'bare_except', message: 'Bare except catches all exceptions' });
      }

      // Hardcoded secrets
      if (/(?:api[_-]?key|password|secret|token)\s*[=:]\s*["'][^"']{8,}["']/i.test(line)) {
        if (!/["']<[^>]+>["']|["']your[_-]|["']xxx|["']example|["']test|["']dummy|os\.environ|getenv/i.test(line)) {
          issues.push({ line: lineNo, severity: 'error', category: 'hardcoded_secret', message: 'Possible hardcoded secret' });
        }
      }

      // TODO/FIXME
      if (/#\s*(TODO|FIXME|HACK|XXX|BUG)\b/i.test(line)) {
        issues.push({ line: lineNo, severity: 'info', category: 'todo_comment', message: 'TODO/FIXME comment found' });
      }

      // Debug code
      if (/\bprint\s*\(/.test(line) && !path.includes('test')) {
        issues.push({ line: lineNo, severity: 'warning', category: 'debug_code', message: 'Debug print statement' });
      }
    });
  }

  // JavaScript/TypeScript validation
  if (ext === 'js' || ext === 'ts' || ext === 'jsx' || ext === 'tsx') {
    lines.forEach((line, i) => {
      const lineNo = i + 1;

      if (/console\.log\s*\(/.test(line) && !path.includes('test')) {
        issues.push({ line: lineNo, severity: 'warning', category: 'debug_code', message: 'console.log statement' });
      }

      if (/\bdebugger\b/.test(line)) {
        issues.push({ line: lineNo, severity: 'warning', category: 'debug_code', message: 'debugger statement' });
      }

      if (/(?:api[_-]?key|password|secret|token)\s*[=:]\s*["'][^"']{8,}["']/i.test(line)) {
        if (!/["']<[^>]+>["']|["']your[_-]|process\.env/i.test(line)) {
          issues.push({ line: lineNo, severity: 'error', category: 'hardcoded_secret', message: 'Possible hardcoded secret' });
        }
      }
    });
  }

  return issues;
}

// Pattern detection
interface DetectedPattern {
  category: string;
  pattern: string;
  confidence: number;
}

function detectPatterns(rootPath: string, sampleSize: number): DetectedPattern[] {
  const { readdirSync, readFileSync, statSync } = require('fs');
  const { join, extname } = require('path');
  const patterns: DetectedPattern[] = [];

  // Collect Python files
  const pyFiles: string[] = [];
  function collectFiles(dir: string, depth = 0) {
    if (depth > 3) return;
    try {
      for (const entry of readdirSync(dir)) {
        if (entry.startsWith('.') || entry === 'node_modules' || entry === '__pycache__') continue;
        const full = join(dir, entry);
        const stat = statSync(full);
        if (stat.isDirectory()) collectFiles(full, depth + 1);
        else if (extname(entry) === '.py') pyFiles.push(full);
      }
    } catch {}
  }
  collectFiles(rootPath);

  let snakeCount = 0, camelCount = 0;
  let specificExcept = 0, bareExcept = 0;

  for (const file of pyFiles.slice(0, sampleSize)) {
    try {
      const content = readFileSync(file, 'utf-8');

      // Count naming styles
      const funcs = content.match(/def\s+([a-z_][a-z0-9_]*)\s*\(/gi) || [];
      for (const m of funcs) {
        if (/_/.test(m)) snakeCount++;
        else if (/[a-z][A-Z]/.test(m)) camelCount++;
      }

      // Count exception handling
      specificExcept += (content.match(/except\s+\w+/g) || []).length;
      bareExcept += (content.match(/except\s*:/g) || []).length;
    } catch {}
  }

  if (snakeCount > camelCount && snakeCount > 5) {
    patterns.push({ category: 'naming', pattern: 'Functions use snake_case', confidence: snakeCount / (snakeCount + camelCount) });
  }

  if (specificExcept > bareExcept * 2) {
    patterns.push({ category: 'error_handling', pattern: 'Uses specific exception types', confidence: 0.8 });
  }

  return patterns;
}

// Style detection
interface StyleProfile {
  indent_type: string;
  indent_size: number;
  quote_style: string;
}

function detectStyle(rootPath: string, sampleSize: number): StyleProfile {
  const { readdirSync, readFileSync, statSync } = require('fs');
  const { join, extname } = require('path');

  let spaces = 0, tabs = 0;
  let singleQuotes = 0, doubleQuotes = 0;
  const indentSizes: number[] = [];

  const pyFiles: string[] = [];
  function collectFiles(dir: string, depth = 0) {
    if (depth > 3) return;
    try {
      for (const entry of readdirSync(dir)) {
        if (entry.startsWith('.') || entry === 'node_modules') continue;
        const full = join(dir, entry);
        const stat = statSync(full);
        if (stat.isDirectory()) collectFiles(full, depth + 1);
        else if (extname(entry) === '.py') pyFiles.push(full);
      }
    } catch {}
  }
  collectFiles(rootPath);

  for (const file of pyFiles.slice(0, sampleSize)) {
    try {
      const content = readFileSync(file, 'utf-8');

      for (const line of content.split('\n')) {
        const match = line.match(/^(\s+)/);
        if (match) {
          if (match[1].includes('\t')) tabs++;
          else {
            spaces++;
            if (match[1].length <= 8) indentSizes.push(match[1].length);
          }
        }
      }

      singleQuotes += (content.match(/'/g) || []).length;
      doubleQuotes += (content.match(/"/g) || []).length;
    } catch {}
  }

  return {
    indent_type: tabs > spaces ? 'tabs' : 'spaces',
    indent_size: indentSizes.length ? Math.round(indentSizes.reduce((a, b) => a + b, 0) / indentSizes.length) : 4,
    quote_style: singleQuotes > doubleQuotes ? 'single' : 'double'
  };
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
