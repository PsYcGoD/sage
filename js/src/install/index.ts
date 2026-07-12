// SAGE AI Agent Injection - 30 tools supported
import { homedir } from 'os';
import { join, dirname } from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { AGENT_TARGETS, SAGE_BLOCK_END, SAGE_BLOCK_START } from './targets.js';

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
    const dir = dirname(fullPath);
    mkdirSync(dir, { recursive: true });
    
    // Create new file with instruction
    writeFileSync(fullPath, target.instruction, 'utf-8');
    return true;
  }

  // Read existing content
  let content = readFileSync(fullPath, 'utf-8');

  if (content.includes(target.instruction)) {
    return false;
  }

  // Replace Python or older npm SAGE managed blocks so the active install path
  // dictates the exact command agents must use.
  if (content.includes(SAGE_BLOCK_START) && content.includes(SAGE_BLOCK_END)) {
    const before = content.split(SAGE_BLOCK_START)[0].trimEnd();
    const after = content.split(SAGE_BLOCK_END).slice(1).join(SAGE_BLOCK_END).trimStart();
    content = `${before}${before ? '\n\n' : ''}${target.instruction.trim()}\n${after ? `\n${after}` : ''}`;
    writeFileSync(fullPath, content, 'utf-8');
    return true;
  }

  // Old unmanaged SAGE text exists. Prepend the npm managed block so new agent
  // sessions see the explicit npx command first.
  if (content.includes('SAGE') && (content.includes('sage run') || content.includes('psycgod-sage-js'))) {
    content = target.instruction + '\n\n' + content;
    writeFileSync(fullPath, content, 'utf-8');
    return true;
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
  if (path.startsWith('~/') || path.startsWith('~\\') || path === '~') {
    // Remove ~ and any leading separator, then join with homedir
    const rest = path.slice(1).replace(/^[/\\]/, '');
    return rest ? join(homedir(), rest) : homedir();
  }
  return path;
}
