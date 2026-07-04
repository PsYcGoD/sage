"""
Simple validation script for SAGE GUI widgets.
Tests that all components can be imported and instantiated.
"""

import sys
import os

# Force UTF-8 encoding for console output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

print("SAGE GUI Widget Validation")
print("=" * 50)

# Test 1: Import configuration
print("\n[1/4] Testing configuration module...")
try:
    from sage.gui.config import get_config, GUIConfig
    config = get_config()
    print("  [OK] Configuration loaded")
    print(f"    - Personal mode: {config.is_personal_mode()}")
    print(f"    - Default AI: {config.get_default_ai()}")
    print(f"    - Config path: {config.config_path}")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")
    sys.exit(1)

# Test 2: Import widgets
print("\n[2/4] Testing widget imports...")
try:
    from sage.gui.widgets import AISelector, InputArea, OutputView, BlockType
    print("  [OK] All widgets imported successfully")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")
    sys.exit(1)

# Test 3: Verify files exist
print("\n[3/4] Verifying files...")
files = [
    "src/sage/gui/config.py",
    "src/sage/gui/widgets/ai_selector.py",
    "src/sage/gui/widgets/input_area.py",
    "src/sage/gui/widgets/output_view.py",
]
for file in files:
    path = os.path.join(os.path.dirname(__file__), file)
    if os.path.exists(path):
        print(f"  [OK] {file}")
    else:
        print(f"  [FAIL] Missing: {file}")
        sys.exit(1)

# Test 4: Configuration functionality
print("\n[4/4] Testing configuration methods...")
try:
    config = get_config()

    # Test method calls
    ai_command = config.get_ai_command('claude')
    prompts = config.get_system_prompts('claude')
    theme = config.get_theme()
    default_ai = config.get_default_ai()

    print(f"  [OK] get_ai_command('claude'): {ai_command}")
    print(f"  [OK] get_system_prompts('claude'): {len(prompts)} prompt(s)")
    print(f"  [OK] get_theme(): {theme}")
    print(f"  [OK] get_default_ai(): {default_ai}")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("[SUCCESS] All validation tests passed!")
print("\nCreated components:")
print("  1. Configuration loader (config.py)")
print("  2. AI Selector widget (ai_selector.py)")
print("  3. Input Area widget (input_area.py)")
print("  4. Output View widget (output_view.py)")
print("\nTo test the GUI interactively, run:")
print("  python test_gui_widgets.py")
