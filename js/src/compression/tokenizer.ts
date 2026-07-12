// Token counting using tiktoken or fallback estimation

let encoder: any = null;

export function countTokens(text: string): number {
  if (!text) return 0;

  // Try tiktoken first
  try {
    if (!encoder) {
      // Lazy load tiktoken
      const tiktoken = require('tiktoken');
      encoder = tiktoken.encoding_for_model('gpt-4');
    }
    return encoder.encode(text).length;
  } catch {
    // Fallback: estimate ~4 chars per token (conservative)
    return Math.ceil(text.length / 4);
  }
}

export function truncateToTokens(text: string, maxTokens: number): string {
  const tokens = countTokens(text);
  
  if (tokens <= maxTokens) {
    return text;
  }

  // Binary search for the right truncation point
  let low = 0;
  let high = text.length;

  while (low < high) {
    const mid = Math.floor((low + high + 1) / 2);
    if (countTokens(text.slice(0, mid)) <= maxTokens) {
      low = mid;
    } else {
      high = mid - 1;
    }
  }

  return text.slice(0, low) + '\n[SAGE] ... truncated ...';
}
