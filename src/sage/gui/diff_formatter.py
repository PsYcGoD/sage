"""
Diff formatter for displaying file edits with syntax highlighting.

Generates visual diffs showing removed (-) and added (+) lines with colors.
"""


def format_edit_diff(file_path: str, old_string: str, new_string: str) -> str:
    """
    Format an Edit() tool call as a visual diff.

    Args:
        file_path: Path to the file being edited
        old_string: Text being removed
        new_string: Text being added

    Returns:
        Formatted diff string with - (removed) and + (added) prefixes
    """
    lines = []

    # Header
    lines.append(f"\n━━━ Edit: {file_path} ━━━")

    # Removed lines (red with -)
    if old_string:
        old_lines = old_string.splitlines()
        lines.append("\n❌ Removed:")
        for line in old_lines:
            lines.append(f"- {line}")

    # Added lines (green with +)
    if new_string:
        new_lines = new_string.splitlines()
        lines.append("\n✅ Added:")
        for line in new_lines:
            lines.append(f"+ {line}")

    lines.append("\n")

    return "\n".join(lines)


def format_write_diff(file_path: str, content: str) -> str:
    """
    Format a Write() tool call showing all content.

    Args:
        file_path: Path to the file being written
        content: File content

    Returns:
        Formatted output with file header and full content
    """
    lines = []

    # Header
    lines.append(f"\n━━━ Write: {file_path} ━━━")

    # Full content
    content_lines = content.splitlines()

    lines.append("\n✅ Created:")
    for line in content_lines:
        lines.append(f"+ {line}")

    lines.append("\n")

    return "\n".join(lines)
