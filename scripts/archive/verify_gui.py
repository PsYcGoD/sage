"""Verification script for SAGE Desktop GUI"""
# -*- coding: utf-8 -*-

print("=== SAGE Desktop GUI Verification ===\n")

# 1. Check imports
print("1. Testing imports...")
try:
    from sage.gui.app import SAGEApp
    from sage.gui.widgets.metric_card import MetricCard
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    exit(1)

# 2. Check dependencies
print("\n2. Checking dependencies...")
try:
    import customtkinter as ctk
    print(f"   ✓ customtkinter {ctk.__version__}")
except ImportError:
    print("   ✗ customtkinter not installed")
    exit(1)

try:
    import PIL
    print(f"   ✓ Pillow {PIL.__version__}")
except ImportError:
    print("   ✗ Pillow not installed")
    exit(1)

try:
    import psutil
    print(f"   ✓ psutil {psutil.__version__}")
except ImportError:
    print("   ✗ psutil not installed")
    exit(1)

# 3. Test database connection and queries
print("\n3. Testing database queries...")
from sage.store import connect

conn = connect()
cursor = conn.cursor()

try:
    # Total Commands
    result = cursor.execute("SELECT COUNT(*) FROM runs").fetchone()
    total_commands = result[0] if result else 0
    print(f"   ✓ Total Commands: {total_commands}")

    # Active Agents
    result = cursor.execute("SELECT COUNT(*) FROM agents WHERE status='busy'").fetchone()
    active_agents = result[0] if result else 0
    print(f"   ✓ Active Agents: {active_agents}")

    # Success Rate
    result = cursor.execute(
        "SELECT AVG(CASE WHEN exit_code=0 THEN 1.0 ELSE 0.0 END) FROM runs"
    ).fetchone()
    success_rate = result[0] if result and result[0] is not None else 0.0
    print(f"   ✓ Success Rate: {success_rate * 100:.1f}%")

except Exception as e:
    print(f"   ✗ Database query failed: {e}")
    exit(1)
finally:
    conn.close()

# 4. Check if GUI is running
print("\n4. Checking if GUI is running...")
import psutil
gui_running = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe':
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('sage' in arg and 'gui' in arg for arg in cmdline):
                gui_running = True
                print(f"   ✓ GUI process found (PID: {proc.info['pid']})")
                break
    except:
        pass

if not gui_running:
    print("   - GUI not currently running (this is okay)")

# 5. Verify files created
print("\n5. Verifying created files...")
import os
files = [
    "src/sage/gui/__init__.py",
    "src/sage/gui/app.py",
    "src/sage/gui/widgets/__init__.py",
    "src/sage/gui/widgets/metric_card.py"
]

for file in files:
    if os.path.exists(file):
        print(f"   ✓ {file}")
    else:
        print(f"   ✗ {file} - MISSING")

print("\n" + "="*50)
print("✓ SAGE Desktop GUI verification complete!")
print("="*50)
print("\nTo launch the GUI, run: sage gui")
print("Or: python -m sage gui")
