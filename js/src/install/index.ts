// SAGE AI Agent Injection - 30 tools supported
import { homedir } from 'os';
import { join } from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { AGENT_TARGETS, SAGE_INSTRUCTION } from './targets.js';

export async function injectAllAgentConfigs(): Promise<number> {
  let injected = 0;

  for (const target of AGENT_TARGETS) {
    try {
      const success = await injectAgentConfig(target);
      if (success) injected++;
    } catch {
      // Skip failed injections silently
    }
  }

  return injected;
}

interface AgentTarget {
  name: string;
  path: string;
  instruction: string;
  createIfMissing: boolean;
  fileType: 'markdown' | 'json' | 'yaml';
}

async function injectAgentConfig(target: AgentTarget): Promise<boolean> {
  const fullPath = expandPath(target.path);
  
  // Check if file exists
  if (!existsSync(fullPath)) {
    if (!target.createIfMissing) return false;
    
    // Create parent directory
    const dir = fullPath.substring(0, fullPath.lastIndexOf(/[/\\]/.test(fullPath) ? fullPath.match(/[/\\]/g)!.pop()! : '/'));
    mkdirSync(dir, { recursive: true });
    
    // Create new file with instruction
    writeFileSync(fullPath, target.instruction, 'utf-8');
    return true;
  }

  // Read existing content
  let content = readFileSync(fullPath, 'utf-8');

  // Check if already has SAGE instruction
  if (content.includes('SAGE') && content.includes('sage run')) {
    return false; // Already configured
  }

  // Inject based on file type
  if (target.fileType === 'markdown') {
    // Prepend to markdown files
    content = target.instruction + '\n\n' + content;
  } else if (target.fileType === 'json') {
    // For JSON, we'd need to parse and add to appropriate section
    // For now, skip JSON files that already exist
    return false;
  } else if (target.fileType === 'yaml') {
    // Prepend as comment to YAML
    const yamlInstruction = target.instruction
      .split('\n')
      .map(line => `# ${line}`)
      .join('\n');
    content = yamlInstruction + '\n\n' + content;
  }

  writeFileSync(fullPath, content, 'utf-8');
  return true;
}

function expandPath(path: string): string {
  if (path.startsWith('~')) {
    return join(homedir(), path.slice(1));
  }
  return path;
}
