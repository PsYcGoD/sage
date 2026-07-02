"""Test script to verify SAGE GUI metrics queries"""

from sage.store import connect

def test_metrics():
    conn = connect()
    cursor = conn.cursor()

    # 1. Total Commands
    result = cursor.execute("SELECT COUNT(*) FROM runs").fetchone()
    total_commands = result[0] if result else 0
    print(f"Total Commands: {total_commands}")

    # 2. Active Agents
    result = cursor.execute("SELECT COUNT(*) FROM agents WHERE status='busy'").fetchone()
    active_agents = result[0] if result else 0
    print(f"Active Agents: {active_agents}")

    # 3. Success Rate
    result = cursor.execute(
        "SELECT AVG(CASE WHEN exit_code=0 THEN 1.0 ELSE 0.0 END) FROM runs"
    ).fetchone()
    success_rate = result[0] if result and result[0] is not None else 0.0
    print(f"Success Rate: {success_rate * 100:.1f}%")

    # 4. List all runs
    result = cursor.execute("SELECT id, command, exit_code FROM runs ORDER BY id DESC LIMIT 5").fetchall()
    print("\nRecent runs:")
    for row in result:
        print(f"  #{row[0]}: {row[1]} (exit={row[2]})")

    conn.close()
    print("\n✓ All database queries working correctly!")

if __name__ == "__main__":
    test_metrics()
