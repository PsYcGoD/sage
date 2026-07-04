"""Replace _fetch_sidebar_data with SessionManager version."""

with open('src/sage/gui/app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find method boundaries
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'def _fetch_sidebar_data(self):' in line:
        start_line = i
    if start_line and lines[i].strip().startswith('except Exception as e:'):
        if i + 1 < len(lines) and 'Sidebar' in lines[i + 1]:
            end_line = i + 2
            break

print(f"Replacing lines {start_line + 1} to {end_line + 1}")

# New method code
new_method = '''    def _fetch_sidebar_data(self):
        """Fetch sidebar data from SessionManager"""
        try:
            # Get all projects with their sessions from SessionManager
            projects = self.session_manager.get_all_projects()

            # Convert to sidebar format
            groups = []
            for project in projects:
                sessions = project.get("sessions", [])
                # Convert sessions to chat format for sidebar
                chats = []
                for session in sessions:
                    chats.append({
                        "id": session.get("id"),
                        "title": session.get("title", "New Chat"),
                        "display_title": session.get("title", "New Chat"),
                        "relative_time": self._format_relative_time(session.get("updated_at", "")),
                        "pinned": session.get("pinned", False),
                        "unread": session.get("unread", False),
                    })

                groups.append({
                    "path": project.get("path"),
                    "name": project.get("name"),
                    "session_count": project.get("session_count", 0),
                    "run_count": project.get("session_count", 0),  # Compat
                    "sessions": chats,
                    "chats": chats,  # Compat with old sidebar code
                })

            # Add current project if not in list
            current_dir = os.getcwd()
            if not any(g["path"] == current_dir for g in groups):
                groups.insert(0, {
                    "path": current_dir,
                    "name": os.path.basename(current_dir) or "Current Directory",
                    "session_count": 0,
                    "run_count": 0,
                    "sessions": [],
                    "chats": [],
                })

            # Sort: current project first, then by most recent activity
            groups.sort(key=lambda g: (g["path"] != current_dir, g.get("session_count", 0) == 0))

            self.after(0, lambda g=groups: self.sidebar.load_project_groups(g))

        except Exception as e:
            print(f"Sidebar Error: {e}")
'''

# Replace the method
new_lines = lines[:start_line] + [new_method] + lines[end_line:]

# Write back
with open('src/sage/gui/app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Replaced _fetch_sidebar_data with SessionManager version")
