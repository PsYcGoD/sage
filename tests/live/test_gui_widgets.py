"""
Test script for SAGE GUI widgets.

Run this to verify that all the widgets work correctly.
"""

import customtkinter as ctk
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sage.gui.widgets import AISelector, InputArea, OutputView
from sage.gui.config import get_config


def test_widgets():
    """Test all GUI widgets."""

    # Create main window
    root = ctk.CTk()
    root.title("SAGE Widget Test")
    root.geometry("800x600")

    # Set theme
    ctk.set_appearance_mode("dark")

    # Test configuration
    print("\n=== Testing Configuration ===")
    config = get_config()
    print(f"Personal mode: {config.is_personal_mode()}")
    print(f"Default AI: {config.get_default_ai()}")
    print(f"Theme: {config.get_theme()}")
    print(f"Claude command: {config.get_ai_command('claude')}")
    print(f"Claude prompts: {config.get_system_prompts('claude')}")

    # Create main container
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Test AI Selector
    print("\n=== Testing AI Selector ===")
    def on_ai_change(ai):
        print(f"AI changed to: {ai}")
        output_view.append_text(f"AI changed to: {ai}\n")

    ai_selector = AISelector(
        main_frame,
        default_ai=config.get_default_ai(),
        callback=on_ai_change
    )
    ai_selector.pack(fill="x", padx=5, pady=5)
    print(f"Current AI: {ai_selector.get_selected_ai()}")

    # Test Output View
    print("\n=== Testing Output View ===")
    output_view = OutputView(main_frame)
    output_view.pack(fill="both", expand=True, padx=5, pady=5)

    # Add sample output with different block types
    output_view.append_text("━━━ Thinking ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    output_view.append_text("Analyzing the test suite structure...\n")
    output_view.append_text("• Found 15 test files\n")
    output_view.append_text("• 3 tests are failing\n\n")

    output_view.append_text("━━━ Running ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    output_view.append_text("$ sage run -- pytest tests/\n")
    output_view.append_text("✓ 12 passed\n")
    output_view.append_text("✗ 3 failed (test_auth.py, test_db.py, test_api.py)\n\n")

    output_view.append_text("━━━ Coding ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    output_view.append_text("Fixing import error in test_auth.py:12\n")
    output_view.append_text("```python\n")
    output_view.append_text("- from auth import verify_token\n")
    output_view.append_text("+ from src.auth import verify_token\n")
    output_view.append_text("```\n\n")

    output_view.append_text("━━━ Complete ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    output_view.append_text("✅ All tests passing! Fixed 3 import errors.\n")
    output_view.append_text("Token savings: 1,247 tokens (96.8% compression)\n\n")

    # Test Input Area
    print("\n=== Testing Input Area ===")
    def on_send(text):
        print(f"Send clicked: {text}")
        output_view.append_text(f"\n> {text}\n\n")
        input_area.clear()

    def on_clear():
        print("Clear clicked")

    def on_permission_change(mode):
        print(f"Permission changed: {mode}")
        output_view.append_text(f"\nPermission mode changed to {mode}\n\n")

    def on_cancel():
        print("Cancel clicked")

    def on_output_theme_toggle():
        print("Output theme toggled")

    input_area = InputArea(
        main_frame,
        on_send=on_send,
        on_clear=on_clear,
        on_permission_change=on_permission_change,
        on_cancel=on_cancel,
        on_output_theme_toggle=on_output_theme_toggle
    )
    input_area.pack(fill="x", padx=5, pady=5)

    print("\nAll widgets loaded successfully!")
    print("\nTry the following:")
    print("1. Change the AI selection")
    print("2. Type a message and click Send or press Ctrl+Enter")
    print("3. Click Clear to clear the input")
    print("4. Change the permission mode")
    print("\nWindow closes automatically after smoke check.")

    # Run the app
    root.after(500, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    print("SAGE GUI Widget Test")
    print("=" * 50)
    test_widgets()
