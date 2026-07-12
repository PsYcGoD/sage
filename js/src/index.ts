// SAGE JavaScript V1 - Main Entry
// Smart Agent Guidance Engine

export { compress, CompressionResult } from './compression/index.js';
export { Database } from './db/index.js';
export { runCommand } from './runner/index.js';
export { startMcpServer } from './mcp/server.js';
export { FailurePredictor } from './ml/index.js';
export { agents, selectAgents } from './agents/index.js';
export { setup, isSetupComplete } from './cli/setup.js';
export { autoConnect } from './api/connect.js';

export const VERSION = '1.0.0';
