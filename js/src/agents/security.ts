// Security Agent - Secrets scanning, vulnerability detection
import type { Agent, AgentAnalysis } from './index.js';

export class SecurityAgent implements Agent {
  type = 'security';
  name = 'Security Agent';
  capabilities = ['audit', 'secrets', 'dependency_risk'];
  triggers = [
    'security', 'secure', 'secret', 'secrets', 'token',
    'password', 'auth', 'oauth', 'credential', 'credentials',
    'api key', 'vulnerability', 'exploit', 'injection',
    'xss', 'csrf', 'permission', 'permissions', 'privacy',
    'redact', 'pii', 'encrypt', 'decrypt', 'audit', 'malware'
  ];
  description = 'Checks security-sensitive changes.';

  analyze(input: string): AgentAnalysis {
    const findings: string[] = [];
    const suggestions: string[] = [];

    // Comprehensive secret patterns
    const secretPatterns = [
      { pattern: /sk-[a-zA-Z0-9]{20,}/g, type: 'OpenAI API key', severity: 'HIGH' },
      { pattern: /ghp_[a-zA-Z0-9]{36}/g, type: 'GitHub personal access token', severity: 'HIGH' },
      { pattern: /gho_[a-zA-Z0-9]{36}/g, type: 'GitHub access token', severity: 'HIGH' },
      { pattern: /github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}/g, type: 'GitHub fine-grained token', severity: 'HIGH' },
      { pattern: /AKIA[A-Z0-9]{16}/g, type: 'AWS Access Key ID', severity: 'CRITICAL' },
      { pattern: /[a-zA-Z0-9/+=]{40}/g, type: 'Possible AWS Secret Key', severity: 'HIGH' },
      { pattern: /xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*/g, type: 'Slack token', severity: 'HIGH' },
      { pattern: /sk_live_[a-zA-Z0-9]{24,}/g, type: 'Stripe live key', severity: 'CRITICAL' },
      { pattern: /sk_test_[a-zA-Z0-9]{24,}/g, type: 'Stripe test key', severity: 'MEDIUM' },
      { pattern: /sq0atp-[a-zA-Z0-9_-]{22}/g, type: 'Square access token', severity: 'HIGH' },
      { pattern: /AIza[a-zA-Z0-9_-]{35}/g, type: 'Google API key', severity: 'MEDIUM' },
      { pattern: /[a-f0-9]{32}-us\d+/g, type: 'Mailchimp API key', severity: 'MEDIUM' },
      { pattern: /key-[a-zA-Z0-9]{32}/g, type: 'Mailgun API key', severity: 'MEDIUM' },
      { pattern: /SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}/g, type: 'SendGrid API key', severity: 'HIGH' },
      { pattern: /-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----/g, type: 'Private key', severity: 'CRITICAL' },
      { pattern: /password\s*[=:]\s*['"][^'"]{8,}['"]/gi, type: 'Hardcoded password', severity: 'HIGH' },
      { pattern: /api[_-]?key\s*[=:]\s*['"][^'"]{16,}['"]/gi, type: 'API key in code', severity: 'HIGH' },
      { pattern: /bearer\s+[a-zA-Z0-9_-]{20,}/gi, type: 'Bearer token', severity: 'HIGH' },
      { pattern: /basic\s+[a-zA-Z0-9+/=]{20,}/gi, type: 'Basic auth credentials', severity: 'HIGH' },
    ];

    for (const { pattern, type, severity } of secretPatterns) {
      const matches = input.match(pattern);
      if (matches) {
        findings.push(`🔴 ${severity}: ${type} detected (${matches.length} occurrence${matches.length > 1 ? 's' : ''})`);
        suggestions.push(`Remove ${type} and use environment variables or secrets manager`);
      }
    }

    // Check for security anti-patterns
    const antiPatterns = [
      { pattern: /eval\s*\(/g, type: 'eval() usage', risk: 'Code injection vulnerability' },
      { pattern: /innerHTML\s*=/g, type: 'innerHTML assignment', risk: 'XSS vulnerability' },
      { pattern: /document\.write/g, type: 'document.write usage', risk: 'XSS vulnerability' },
      { pattern: /SELECT.*FROM.*WHERE.*\+/gi, type: 'String concatenation in SQL', risk: 'SQL injection' },
      { pattern: /exec\s*\(/g, type: 'exec() usage', risk: 'Command injection' },
      { pattern: /shell\s*=\s*True/g, type: 'shell=True in subprocess', risk: 'Command injection' },
      { pattern: /verify\s*=\s*False/gi, type: 'SSL verification disabled', risk: 'MITM vulnerability' },
      { pattern: /disable.*ssl|ssl.*disable/gi, type: 'SSL disabled', risk: 'MITM vulnerability' },
    ];

    for (const { pattern, type, risk } of antiPatterns) {
      if (pattern.test(input)) {
        findings.push(`⚠️ ${type} - ${risk}`);
        suggestions.push(`Review and fix: ${type}`);
      }
    }

    // Check for PII patterns
    const piiPatterns = [
      { pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, type: 'Email addresses' },
      { pattern: /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, type: 'Phone numbers' },
      { pattern: /\b\d{3}[-]?\d{2}[-]?\d{4}\b/g, type: 'SSN-like numbers' },
      { pattern: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/g, type: 'Credit card numbers' },
    ];

    for (const { pattern, type } of piiPatterns) {
      const matches = input.match(pattern);
      if (matches && matches.length > 2) {
        findings.push(`⚠️ Possible PII: ${type} (${matches.length} occurrences)`);
        suggestions.push(`Review if ${type} should be redacted`);
      }
    }

    // Dependency vulnerabilities (if npm audit or similar output)
    if (input.toLowerCase().includes('vulnerabilit')) {
      const critMatch = input.match(/(\d+)\s*critical/i);
      const highMatch = input.match(/(\d+)\s*high/i);
      const modMatch = input.match(/(\d+)\s*moderate/i);

      if (critMatch) findings.push(`🔴 ${critMatch[1]} critical vulnerabilities`);
      if (highMatch) findings.push(`🟠 ${highMatch[1]} high vulnerabilities`);
      if (modMatch) findings.push(`🟡 ${modMatch[1]} moderate vulnerabilities`);

      if (critMatch || highMatch) {
        suggestions.push('Run npm audit fix or update vulnerable packages');
        suggestions.push('Review breaking changes before updating major versions');
      }
    }

    // Summary
    if (findings.length === 0) {
      findings.push('✓ No security issues detected');
    }

    return {
      agent: this.name,
      score: findings.some(f => f.includes('CRITICAL')) ? 0.2 : 
             findings.some(f => f.includes('HIGH')) ? 0.5 : 
             findings.length > 1 ? 0.7 : 1.0,
      findings,
      suggestions
    };
  }
}
