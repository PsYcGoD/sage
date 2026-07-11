export interface Session {
  id: string;
  title: string;
  project: string;
  created_at: string;
  updated_at: string;
  preview: string;
  pinned: boolean;
  unread: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  thinking?: string;
  tool_calls?: ToolCall[];
  agent_analysis?: AgentAnalysis;
  provider?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  input: string;
  output: string;
  status: 'running' | 'success' | 'error';
  duration_ms?: number;
  sage_summary?: string;
}

export interface AgentAnalysis {
  agents_used: string[];
  tokens: number;
  ml_prediction?: { confidence: number; prediction: string };
  duration_ms: number;
}

export interface Provider {
  id: string;
  name: string;
  model: string;
  status: 'connected' | 'disconnected' | 'error';
}

export interface WSMessage {
  type: string;
  payload: any;
  id?: string;
}

export interface WindowAPI {
  minimize: () => void;
  maximize: () => void;
  close: () => void;
  isMaximized: () => Promise<boolean>;
  onMaximizedChange: (callback: (maximized: boolean) => void) => void;
}

export interface DialogAPI {
  pickFolder: () => Promise<string | null>;
}

declare global {
  interface Window {
    electronAPI: {
      window: WindowAPI;
      dialog: DialogAPI;
      platform: string;
    };
  }
}
