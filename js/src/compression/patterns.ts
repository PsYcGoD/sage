// Error detection patterns
export const ERROR_PATTERNS: RegExp[] = [
  // General errors
  /error[:\s]/i,
  /exception[:\s]/i,
  /failed[:\s]/i,
  /failure[:\s]/i,
  /fatal[:\s]/i,
  /panic[:\s]/i,
  
  // Python
  /traceback/i,
  /^.*error:.*$/i,
  /importerror/i,
  /syntaxerror/i,
  /typeerror/i,
  /valueerror/i,
  /keyerror/i,
  /attributeerror/i,
  /nameerror/i,
  /indexerror/i,
  /modulenotfounderror/i,
  
  // JavaScript/Node
  /referenceerror/i,
  /uncaught/i,
  /unhandled/i,
  /cannot find module/i,
  /is not defined/i,
  /is not a function/i,
  /cannot read propert/i,
  
  // Rust
  /error\[e\d+\]/i,
  /cannot find/i,
  /mismatched types/i,
  
  // Go
  /undefined:/i,
  /cannot use/i,
  
  // Build tools
  /build failed/i,
  /compilation failed/i,
  /npm err!/i,
  /yarn error/i,
  /pip error/i,
  /cargo error/i,
  
  // Tests
  /assert.*failed/i,
  /test.*failed/i,
  /failed.*test/i,
  /\d+ failed/i,
  
  // General
  /permission denied/i,
  /access denied/i,
  /not found/i,
  /no such file/i,
  /command not found/i,
  /timeout/i,
  /connection refused/i,
  /segmentation fault/i,
  /out of memory/i,
  /stack overflow/i,
];

// Noise patterns to remove
export const NOISE_PATTERNS: RegExp[] = [
  // Progress bars and spinners
  /[⠀-⣿]+/g,  // Braille patterns
  /[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]+/g,  // Spinner chars
  /\[[\s=>#-]*\]\s*\d+%/g,  // Progress bars [=====>  ] 50%
  /\.{4,}/g,  // Long dots
  
  // ANSI escape codes
  /\x1b\[[0-9;]*m/g,
  /\x1b\[\d+[A-Za-z]/g,
  
  // Timestamps in logs (but keep the message)
  /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]\d+\s*/gm,
  
  // npm install noise
  /added \d+ packages.*$/gm,
  /^npm warn.*$/gm,
  
  // pip install noise
  /^Collecting .*/gm,
  /^Downloading .*/gm,
  /^Installing collected packages.*/gm,
  /^Successfully installed.*/gm,
  
  // Git noise
  /^remote: Counting objects:.*/gm,
  /^remote: Compressing objects:.*/gm,
  /^Receiving objects:.*/gm,
  /^Resolving deltas:.*/gm,
];

// Threshold for duplicate detection
export const DUPLICATE_THRESHOLD = 80;
