// SAGE Agents - 4 core agents (code, debug, test, security)
import { CodeAgent } from './code.js';
import { DebugAgent } from './debug.js';
import { TestAgent } from './test.js';
import { SecurityAgent } from './security.js';

export interface Agent {
  type: string;
  name: string;
  capabilities: string[];
  triggers: string[];
  description: string;
  analyze(input: string): AgentAnalysis;
}

export interface AgentAnalysis {
  agent: string;
  score: number;
  findings: string[];
  suggestions: string[];
}

// 4 Core Agents
export const agents: Agent[] = [
  new CodeAgent(),
  new DebugAgent(),
  new TestAgent(),
  new SecurityAgent()
];

export function selectAgents(input: string, limit: number = 4): Agent[] {
  const text = input.toLowerCase();
  const scored: { agent: Agent; score: number }[] = [];

  for (const agent of agents) {
    let score = 0;
    
    // Check triggers
    for (const trigger of agent.triggers) {
      if (text.includes(trigger.toLowerCase())) {
        score += 100;
      }
    }
    
    // Check capabilities
    for (const capability of agent.capabilities) {
      if (text.includes(capability.toLowerCase())) {
        score += 50;
      }
    }

    if (score > 0) {
      scored.push({ agent, score });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, limit).map(s => s.agent);
}

export function getAgent(type: string): Agent | undefined {
  return agents.find(a => a.type === type);
}

export function listAgents(): { type: string; name: string; description: string }[] {
  return agents.map(a => ({
    type: a.type,
    name: a.name,
    description: a.description
  }));
}
