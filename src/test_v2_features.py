"""Test the new SAGE v2.0 features."""

import asyncio
from sage.autofix import AutoFixEngine
from sage.agents import Orchestrator
from sage.agents.specialized import CodeAgent, TestAgent, DebugAgent


def test_autofix_engine():
    """Test auto-fix engine."""
    print("\n=== Testing Auto-Fix Engine ===")
    
    engine = AutoFixEngine()
    
    # Simulate Python ModuleNotFoundError
    stderr = "ModuleNotFoundError: No module named 'requests'"
    result = engine.analyze_and_fix(
        stdout="",
        stderr=stderr,
        exit_code=1,
        command="python test.py",
        apply=False,
        min_confidence=0.8,
    )
    
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Fix: {result.fix_applied}")
    print(f"Success: {result.success}")
    if result.error_message:
        print(f"Message: {result.error_message}")


async def test_multi_agent():
    """Test multi-agent orchestration."""
    print("\n=== Testing Multi-Agent System ===")
    
    orchestrator = Orchestrator()
    
    # Spawn agents
    code_agent = await orchestrator.spawn_agent(CodeAgent, "code-1")
    test_agent = await orchestrator.spawn_agent(TestAgent, "test-1")
    debug_agent = await orchestrator.spawn_agent(DebugAgent, "debug-1")
    
    # Assign tasks
    await orchestrator.assign_task(
        "code-1",
        "Implement user authentication",
        {"module": "auth", "priority": "high"},
    )
    
    await orchestrator.assign_task(
        "test-1",
        "Generate tests for auth module",
        {"target": "auth.py"},
    )
    
    # Wait a bit for agents to process
    await asyncio.sleep(0.5)
    
    print(f"Active agents: {len(orchestrator.agents)}")
    for name, agent in orchestrator.agents.items():
        print(f"  {name}: {agent.status} ({agent.agent_type})")
    
    await orchestrator.shutdown()


if __name__ == "__main__":
    test_autofix_engine()
    asyncio.run(test_multi_agent())
    print("\n[OK] All tests completed!")
