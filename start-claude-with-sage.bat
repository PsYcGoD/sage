@echo off
REM Start Claude Code with SAGE integration
echo Starting Claude Code with SAGE V2.0 integration...
echo.
echo SAGE Features Available:
echo   - 99.3%% token compression
echo   - Auto-fix engine with ML
echo   - Multi-agent orchestration
echo   - 6 MCP tools ready
echo.
echo Dashboard: http://localhost:8765
echo.

cd /d "%~dp0"
claude --dangerously-skip-permissions --append-system-prompt-file "C:\Users\Admin\.claude\CLAUDE-FABLE-5.md" --append-system-prompt-file "C:\Users\Admin\.claude\SAGE-INTEGRATION.md"
