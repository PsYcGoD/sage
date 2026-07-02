"""Output compression for context efficiency."""

from __future__ import annotations

import difflib
import re
from typing import List


def compress_output(output: str, max_lines: int = 50) -> str:
    """
    Compress command output to save context.
    
    Strategies:
    - Remove duplicate lines
    - Collapse repeated patterns
    - Keep first and last N lines if too long
    - Remove debug/verbose output
    """
    if not output:
        return ""
    
    lines = output.splitlines()
    
    # Remove common noise
    lines = [line for line in lines if not _is_noise(line)]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    # If still too long, keep first and last
    if len(unique_lines) > max_lines:
        keep = max_lines // 2
        compressed = unique_lines[:keep]
        compressed.append(f"... [{len(unique_lines) - max_lines} lines hidden] ...")
        compressed.extend(unique_lines[-keep:])
        return "\n".join(compressed)
    
    return "\n".join(unique_lines)


def smart_diff(file_before: str, file_after: str, context_lines: int = 3) -> str:
    """
    Generate smart diff showing only changes.
    
    Much more context-efficient than full files.
    """
    before_lines = file_before.splitlines()
    after_lines = file_after.splitlines()
    
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        lineterm='',
        n=context_lines
    )
    
    return "\n".join(diff)


def summarize_long_output(output: str, max_chars: int = 1000) -> str:
    """Summarize very long output."""
    if len(output) <= max_chars:
        return output
    
    lines = output.splitlines()
    
    # Extract key information
    errors = [line for line in lines if _is_error(line)]
    warnings = [line for line in lines if _is_warning(line)]
    
    summary_parts = []
    
    if errors:
        summary_parts.append(f"Errors ({len(errors)}):")
        summary_parts.extend(errors[:5])
    
    if warnings:
        summary_parts.append(f"Warnings ({len(warnings)}):")
        summary_parts.extend(warnings[:3])
    
    summary_parts.append(f"\n[Full output: {len(output)} chars, {len(lines)} lines]")
    
    return "\n".join(summary_parts)


def extract_stacktrace(output: str) -> str:
    """Extract just the stacktrace from output."""
    lines = output.splitlines()
    
    # Find traceback
    trace_start = -1
    for i, line in enumerate(lines):
        if "Traceback" in line or "Error" in line or "Exception" in line:
            trace_start = i
            break
    
    if trace_start >= 0:
        return "\n".join(lines[trace_start:])
    
    return output


def _is_noise(line: str) -> bool:
    """Check if line is debug/verbose noise."""
    noise_patterns = [
        r'^\s*$',  # Empty lines
        r'^DEBUG:',
        r'^TRACE:',
        r'^\[.*\] DEBUG',
        r'^    at .*\(internal/',  # Internal stack frames
    ]
    
    for pattern in noise_patterns:
        if re.match(pattern, line):
            return True
    
    return False


def _is_error(line: str) -> bool:
    """Check if line contains error."""
    error_keywords = ['error', 'exception', 'failed', 'fatal']
    line_lower = line.lower()
    return any(kw in line_lower for kw in error_keywords)


def _is_warning(line: str) -> bool:
    """Check if line contains warning."""
    return 'warning' in line.lower() or 'warn:' in line.lower()


def compress_file_content(content: str, max_lines: int = 100) -> str:
    """
    Compress file content for context efficiency.
    
    Show structure + key parts, hide boilerplate.
    """
    lines = content.splitlines()
    
    if len(lines) <= max_lines:
        return content
    
    # Keep imports at top
    imports = []
    code = []
    
    in_imports = True
    for line in lines:
        if in_imports and (line.startswith('import ') or line.startswith('from ')):
            imports.append(line)
        else:
            in_imports = False
            code.append(line)
    
    # Compress code part
    if len(code) > max_lines - len(imports):
        keep = (max_lines - len(imports)) // 2
        code = code[:keep] + [f"... [{len(code) - (keep * 2)} lines hidden] ..."] + code[-keep:]
    
    return "\n".join(imports + code)
