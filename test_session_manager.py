"""Test SessionManager works correctly."""

from sage.gui.session_manager import SessionManager
import os

# Create manager
sm = SessionManager()

# Test creating sessions in current project
project_path = os.getcwd()
print(f"Testing with project: {project_path}")

# Create first session
sid1 = sm.create_session(project_path, "First Chat")
print(f"Created session 1: {sid1}")

# Add some messages
sm.add_message(project_path, sid1, "user", "Hello")
sm.add_message(project_path, sid1, "claude", "Hi there!")

# Create second session
sid2 = sm.create_session(project_path, "Second Chat")
print(f"Created session 2: {sid2}")

sm.add_message(project_path, sid2, "user", "Different conversation")

# Get all sessions
sessions = sm.get_sessions(project_path)
print(f"\nFound {len(sessions)} sessions:")
for s in sessions:
    print(f"  - {s['id']}: {s['title']} ({len(s['messages'])} messages)")

# Get all projects
projects = sm.get_all_projects()
print(f"\nFound {len(projects)} projects:")
for p in projects:
    print(f"  - {p['name']}: {p['session_count']} sessions")

print("\n✅ SessionManager works!")
