// SAGE MCP Server - Model Context Protocol integration
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { TOOLS, handleToolCall } from './tools.js';

const DEFAULT_IDLE_TIMEOUT_MS = 300_000;
const MIN_IDLE_TIMEOUT_MS = 10_000;

function getIdleTimeoutMs(): number {
  const raw = process.env.SAGE_MCP_IDLE_TIMEOUT_SECONDS;
  if (!raw) return DEFAULT_IDLE_TIMEOUT_MS;

  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed)) return DEFAULT_IDLE_TIMEOUT_MS;
  return Math.max(parsed * 1000, MIN_IDLE_TIMEOUT_MS);
}

export async function startMcpServer(): Promise<void> {
  const idleTimeoutMs = getIdleTimeoutMs();
  let idleTimer: NodeJS.Timeout | undefined;

  const touchActivity = () => {
    if (idleTimer) {
      clearTimeout(idleTimer);
    }
    idleTimer = setTimeout(() => {
      console.error(`[SAGE MCP Server] idle for ${Math.round(idleTimeoutMs / 1000)}s; exiting`);
      process.exit(0);
    }, idleTimeoutMs);
    idleTimer.unref?.();
  };

  const server = new Server(
    {
      name: 'sage',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // List available tools
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    touchActivity();
    return { tools: TOOLS };
  });

  // Handle tool calls
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    touchActivity();
    const { name, arguments: args } = request.params;
    
    try {
      const result = await handleToolCall(name, args || {});
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        content: [{ type: 'text', text: `Error: ${message}` }],
        isError: true,
      };
    }
  });

  // Start server
  const transport = new StdioServerTransport();
  touchActivity();
  console.error(`[SAGE MCP Server] stdio ready (idle timeout ${Math.round(idleTimeoutMs / 1000)}s)`);
  await server.connect(transport);
}

// Run if called directly
if (process.argv[1]?.endsWith('server.js') || process.argv[1]?.endsWith('server.ts')) {
  startMcpServer().catch(console.error);
}
