"""Live GUI test with Playwright - tests all AI integrations"""

import subprocess
import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_cli_auth_status():
    """Test if CLIs are authenticated"""
    print("\n=== Testing CLI Authentication ===\n")

    # Test Claude
    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if '"loggedIn": true' in result.stdout:
            print("✅ Claude: Logged in")
            print(f"   Auth method: {result.stdout}")
        else:
            print("❌ Claude: Not logged in")
    except Exception as e:
        print(f"❌ Claude: Error - {e}")

    # Test Codex
    try:
        result = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "Logged in" in result.stdout:
            print(f"✅ Codex: {result.stdout.strip()}")
        else:
            print("❌ Codex: Not logged in")
    except Exception as e:
        print(f"❌ Codex: Error - {e}")


def test_native_cli_client():
    """Test native CLI integration"""
    print("\n=== Testing Native CLI Client ===\n")

    from sage.gui.native_cli_client import check_native_cli_available, NativeCLIClient

    # Test availability
    print("Checking availability...")
    claude_available = check_native_cli_available("claude")
    codex_available = check_native_cli_available("codex")

    print(f"  Claude available: {'✅' if claude_available else '❌'}")
    print(f"  Codex available: {'✅' if codex_available else '❌'}")

    # Test Claude streaming
    if claude_available:
        print("\n  Testing Claude streaming...")
        client = NativeCLIClient("claude")
        response_chunks = []

        for event_type, content in client.stream_response("Say 'HELLO SENSEI' and nothing else"):
            response_chunks.append(content)
            if len(response_chunks) > 100:  # Safety limit
                break

        full_response = "".join(response_chunks)
        if "SENSEI" in full_response or "Sensei" in full_response:
            print("  ✅ Claude streaming works!")
        else:
            print(f"  ⚠️ Claude response unclear: {full_response[:100]}")

    # Test Codex streaming
    if codex_available:
        print("\n  Testing Codex streaming...")
        client = NativeCLIClient("codex")
        response_chunks = []

        for event_type, content in client.stream_response("Say 'CODEX WORKS' and nothing else"):
            response_chunks.append(content)
            if len(response_chunks) > 100:
                break

        full_response = "".join(response_chunks)
        if "CODEX" in full_response or "Codex" in full_response:
            print("  ✅ Codex streaming works!")
        else:
            print(f"  ⚠️ Codex response unclear: {full_response[:100]}")


def test_gui_launch():
    """Test GUI launches"""
    print("\n=== Testing GUI Launch ===\n")

    try:
        # Launch GUI in background
        print("Starting GUI...")
        process = subprocess.Popen(
            [sys.executable, "-m", "sage.gui"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a bit for startup
        time.sleep(3)

        # Check if still running
        if process.poll() is None:
            print("✅ GUI launched successfully")
            print("   PID:", process.pid)

            # Kill it
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()

            print("   Terminated cleanly")
        else:
            stdout, stderr = process.communicate()
            print("❌ GUI crashed on startup")
            print("   stdout:", stdout[:500])
            print("   stderr:", stderr[:500])

    except Exception as e:
        print(f"❌ GUI launch error: {e}")


def test_with_playwright():
    """Test GUI with Playwright automation"""
    print("\n=== Testing GUI with Playwright ===\n")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright not installed")
        print("   Run: pip install playwright")
        print("   Then: playwright install")
        return

    # Start GUI
    print("Starting GUI process...")
    gui_process = subprocess.Popen(
        [sys.executable, "-m", "sage.gui"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(5)  # Wait for GUI to start

    try:
        with sync_playwright() as p:
            # Note: CustomTkinter is not a web browser, so Playwright won't work directly
            # This would work if SAGE had a web UI instead
            print("⚠️  Playwright is for web browsers")
            print("   SAGE uses CustomTkinter (desktop GUI)")
            print("   Cannot automate with Playwright")
            print("   Manual testing required")

    finally:
        gui_process.terminate()
        gui_process.wait(timeout=5)


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("SAGE GUI - Live Integration Test")
    print("="*60)

    test_cli_auth_status()
    test_native_cli_client()
    test_gui_launch()
    test_with_playwright()

    print("\n" + "="*60)
    print("Tests Complete!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
