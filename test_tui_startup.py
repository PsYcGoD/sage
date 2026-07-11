"""Test TUI startup without actually running it."""
import sys
import os
sys.path.insert(0, "src")

# Set a dummy API key for testing
os.environ["ANTHROPIC_API_KEY"] = "test-key-for-startup-check"

try:
    from sage.tui.app import SAGETUIApp
    
    # Try to instantiate the app
    app = SAGETUIApp()
    
    print("✓ App instantiated successfully")
    print(f"✓ Project: {app._project_name}")
    print(f"✓ Project path: {app._project_path}")
    print(f"✓ Session store initialized: {app._store is not None}")
    print(f"✓ Tools registry initialized: {app._tools is not None}")
    print(f"✓ Context manager initialized: {app._context is not None}")
    
    # Check components
    print(f"✓ Current session ID: {app._current_session_id}")
    
    # Try to get sessions
    sessions = app._store.list_sessions(limit=5)
    print(f"✓ Found {len(sessions)} existing sessions")
    
    print("\nAll startup checks passed! The TUI should launch successfully.")
    print("To actually run it: sage tui")
    
except Exception as e:
    print(f"✗ Error during startup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
