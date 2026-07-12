// ML V1 Failure Patterns

export interface RiskPattern {
  pattern: RegExp;
  risk: number;
  reason: string;
}

export interface SafePattern {
  pattern: RegExp;
  reason: string;
}

// High-risk patterns - likely to cause problems
export const RISKY_PATTERNS: RiskPattern[] = [
  // Destructive commands
  { pattern: /rm\s+-rf?\s+\//, risk: 0.95, reason: 'Destructive: rm -rf on root path' },
  { pattern: /rm\s+-rf?\s+~/, risk: 0.9, reason: 'Destructive: rm -rf on home directory' },
  { pattern: /rm\s+-rf?\s+\*/, risk: 0.85, reason: 'Destructive: rm -rf with wildcard' },
  { pattern: /del\s+\/[sq]/, risk: 0.85, reason: 'Destructive: Windows del with /s or /q' },
  { pattern: /format\s+[a-z]:/, risk: 0.95, reason: 'Destructive: disk format' },
  
  // Force flags without safety
  { pattern: /--force(?!\s+--dry)/, risk: 0.6, reason: 'Force flag without dry-run' },
  { pattern: /git\s+push\s+--force/, risk: 0.7, reason: 'Force push (may overwrite history)' },
  { pattern: /git\s+reset\s+--hard/, risk: 0.65, reason: 'Hard reset (may lose changes)' },
  
  // Elevated privileges
  { pattern: /sudo\s+rm/, risk: 0.75, reason: 'Sudo with delete' },
  { pattern: /sudo\s+chmod\s+777/, risk: 0.7, reason: 'Sudo chmod 777 (insecure permissions)' },
  
  // Network operations without checks
  { pattern: /curl.*\|\s*(bash|sh)/, risk: 0.8, reason: 'Pipe curl to shell (unsafe)' },
  { pattern: /wget.*\|\s*(bash|sh)/, risk: 0.8, reason: 'Pipe wget to shell (unsafe)' },
];

// Medium-risk patterns - may fail but recoverable
export const FAILURE_PATTERNS: RiskPattern[] = [
  // Missing dependencies common
  { pattern: /pip\s+install.*--upgrade/, risk: 0.35, reason: 'Upgrade may break dependencies' },
  { pattern: /npm\s+install.*--legacy-peer-deps/, risk: 0.4, reason: 'Legacy peer deps flag suggests conflicts' },
  
  // Environment issues
  { pattern: /python\s+.*\.py\s*$/, risk: 0.25, reason: 'Python script (may have import errors)' },
  { pattern: /node\s+.*\.js\s*$/, risk: 0.25, reason: 'Node script (may have module errors)' },
  
  // Build commands
  { pattern: /npm\s+run\s+build/, risk: 0.3, reason: 'Build command (may have compilation errors)' },
  { pattern: /cargo\s+build/, risk: 0.3, reason: 'Rust build (may have type errors)' },
  { pattern: /make\s+all/, risk: 0.35, reason: 'Make all (may have missing deps)' },
  
  // Test commands (expected to sometimes fail)
  { pattern: /pytest/, risk: 0.4, reason: 'Tests (some may fail)' },
  { pattern: /npm\s+test/, risk: 0.4, reason: 'Tests (some may fail)' },
  { pattern: /jest/, risk: 0.4, reason: 'Tests (some may fail)' },
  
  // Database operations
  { pattern: /drop\s+table/i, risk: 0.6, reason: 'Database drop (destructive)' },
  { pattern: /truncate/i, risk: 0.55, reason: 'Database truncate (destructive)' },
  { pattern: /migrate/, risk: 0.35, reason: 'Migration (may have schema conflicts)' },
];

// Safe patterns - low risk
export const SAFE_PATTERNS: SafePattern[] = [
  // Read-only operations
  { pattern: /--version/, reason: 'Version check (read-only)' },
  { pattern: /--help/, reason: 'Help command (read-only)' },
  { pattern: /ls\s/, reason: 'List directory (read-only)' },
  { pattern: /dir\s/, reason: 'List directory (read-only)' },
  { pattern: /cat\s/, reason: 'View file (read-only)' },
  { pattern: /type\s/, reason: 'View file (read-only)' },
  { pattern: /head\s/, reason: 'View file head (read-only)' },
  { pattern: /tail\s/, reason: 'View file tail (read-only)' },
  { pattern: /grep\s/, reason: 'Search (read-only)' },
  { pattern: /find\s/, reason: 'Find files (read-only)' },
  
  // Git read operations
  { pattern: /git\s+status/, reason: 'Git status (read-only)' },
  { pattern: /git\s+log/, reason: 'Git log (read-only)' },
  { pattern: /git\s+diff/, reason: 'Git diff (read-only)' },
  { pattern: /git\s+branch/, reason: 'Git branch (read-only)' },
  
  // Safe with dry-run
  { pattern: /--dry-run/, reason: 'Dry-run mode (no changes)' },
  { pattern: /--check/, reason: 'Check mode (no changes)' },
  { pattern: /-n(?:\s|$)/, reason: 'Dry-run flag (no changes)' },
  
  // Info commands
  { pattern: /which\s/, reason: 'Which command (read-only)' },
  { pattern: /where\s/, reason: 'Where command (read-only)' },
  { pattern: /echo\s/, reason: 'Echo (display only)' },
  { pattern: /pwd/, reason: 'Print working directory' },
];
