# Start Claude Code with SAGE integration
Write-Host "Starting Claude Code with SAGE V2.0 integration..." -ForegroundColor Cyan
Write-Host ""
Write-Host "SAGE Features Available:" -ForegroundColor Green
Write-Host "  - 99.3% token compression" -ForegroundColor White
Write-Host "  - Auto-fix engine with ML" -ForegroundColor White
Write-Host "  - Multi-agent orchestration" -ForegroundColor White
Write-Host "  - 6 MCP tools ready" -ForegroundColor White
Write-Host ""
Write-Host "Dashboard: http://localhost:8765" -ForegroundColor Yellow
Write-Host ""

Set-Location D:\work\sage
claude --dangerously-skip-permissions --append-system-prompt-file "C:\Users\Admin\.claude\CLAUDE-FABLE-5.md" --append-system-prompt-file "C:\Users\Admin\.claude\SAGE-INTEGRATION.md"
